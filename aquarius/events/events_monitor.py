#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from distutils.util import strtobool
from threading import Thread

import elasticsearch
from jsonsempai import magic  # noqa: F401

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import get_bool_env_value, get_allowed_publishers
from aquarius.block_utils import BlockProcessingClass
from aquarius.config import get_version
from aquarius.retry_mechanism import RetryMechanism
from aquarius.events.constants import EventTypes
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataStateProcessor,
    TransferProcessor,
    MetadataUpdatedProcessor,
    OrderStartedProcessor,
    TokenURIUpdatedProcessor,
)
from aquarius.events.purgatory import Purgatory
from aquarius.events.ve_allocate import VeAllocate
from aquarius.events.util import (
    get_metadata_start_block,
    get_defined_block,
    get_fre,
    get_dispenser,
    is_approved_fre,
    is_approved_dispenser,
)
from artifacts import ERC20Template, ERC721Template
from web3.logs import DISCARD

logger = logging.getLogger(__name__)


class EventsMonitor(BlockProcessingClass):
    """Detect on-chain published Metadata and cache it in the database for
    fast retrieval and searchability.

    The published metadata is extracted from the `MetadataCreated`
    event log from the `Metadata` smartcontract. Metadata updates are also detected using
    the `MetadataUpdated` event.

    The Metadata json object is expected to be
    in an `lzma` compressed form and then encrypted. Decryption is done through Provider.

    The events monitor pauses for 25 seconds between updates.

    The cached Metadata can be restricted to only those published by specific ethereum accounts.
    To do this set the `ALLOWED_PUBLISHERS` envvar to the list of ethereum addresses of known publishers.



    """

    _instance = None

    def __init__(self, web3, config_file):
        self._es_instance = ElasticsearchInstance(config_file)

        self._other_db_index = f"{self._es_instance.db_index}_plus"
        self._es_instance.es.indices.create(index=self._other_db_index, ignore=400)

        self._retries_db_index = f"{self._es_instance.db_index}_retries"
        self._es_instance.es.indices.create(index=self._retries_db_index, ignore=400)

        self._web3 = web3

        self._chain_id = self._web3.eth.chain_id
        self.add_chain_id_to_chains_list()
        self._index_name = "events_last_block_" + str(self._chain_id)
        self._start_block = get_metadata_start_block()

        if get_bool_env_value("EVENTS_CLEAN_START", 0):
            self.reset_chain()

        self.get_or_set_last_block()
        self._allowed_publishers = get_allowed_publishers()
        logger.debug(f"allowed publishers: {self._allowed_publishers}")

        default_sleep_time = 10
        try:
            self._monitor_sleep_time = int(
                os.getenv("OCN_EVENTS_MONITOR_QUITE_TIME", default_sleep_time)
            )
        except ValueError:
            self._monitor_sleep_time = default_sleep_time

        self._monitor_sleep_time = max(self._monitor_sleep_time, default_sleep_time)

        self.purgatory = (
            Purgatory(self._es_instance)
            if (os.getenv("ASSET_PURGATORY_URL") or os.getenv("ACCOUNT_PURGATORY_URL"))
            else None
        )

        self.ve_allocate = (
            VeAllocate(self._es_instance) if (os.getenv("VEALLOCATE_URL")) else None
        )
        allocate_message = (
            "VeAllocate enabled" if self.ve_allocate else "VeAllocate disabled"
        )
        logger.info(allocate_message)
        self.retry_mechanism = RetryMechanism(
            config_file, self._es_instance, self._retries_db_index, self.purgatory
        )

        purgatory_message = (
            "Purgatory enabled" if self.purgatory else "Purgatory disabled"
        )
        logger.info(purgatory_message)
        self._thread_process_blocks_is_on = False
        self._thread_process_queue_is_on = False
        self._thread_process_ve_allocate_is_on = False
        self._thread_process_purgatory_is_on = False

    @property
    def block_envvar(self):
        return "METADATA_CONTRACT_BLOCK"

    def stop_monitor(self):
        """Stops all threads for processing more data"""
        self._thread_process_blocks_is_on = False
        self._thread_process_queue_is_on = False
        self._thread_process_ve_allocate_is_on = False
        self._thread_process_purgatory_is_on = False

    def start_events_monitor(self):
        """Starts all needed threads, depending on config"""
        logger.info("Starting the threads..")
        t = Thread(target=self.thread_process_blocks, daemon=True)
        self._thread_process_blocks_is_on = True
        t.start()
        if strtobool(os.getenv("PROCESS_RETRY_QUEUE", "0")):
            t = Thread(target=self.thread_process_queue, daemon=True)
            self._thread_process_queue_is_on = True
            t.start()
        if self.ve_allocate:
            t = Thread(target=self.thread_process_ve_allocate, daemon=True)
            self._thread_process_ve_allocate_is_on = True
            t.start()
        if self.purgatory:
            t = Thread(target=self.thread_process_purgatory, daemon=True)
            self._thread_process_purgatory_is_on = True
            t.start()

    # main threads below
    def thread_process_blocks(self):
        while True:
            if self._thread_process_blocks_is_on:
                try:
                    logger.info("Starting process_current_blocks ....")
                    self.process_current_blocks()
                except (KeyError, Exception) as e:
                    logger.error(f"Error processing event: {str(e)}.")
            time.sleep(self._monitor_sleep_time)

    def thread_process_queue(self):
        while True:
            if self._thread_process_queue_is_on:
                try:
                    logger.info("Starting process_queue ....")
                    self.retry_mechanism.process_queue()
                except (KeyError, Exception) as e:
                    logger.error(f"Error processing event: {str(e)}.")
            time.sleep(self._monitor_sleep_time)

    def thread_process_ve_allocate(self):
        while True:
            if self._thread_process_ve_allocate_is_on:
                logger.info("Starting ve_allocate.update_lists ....")
                try:
                    self.ve_allocate.update_lists()
                except (KeyError, Exception) as e:
                    logger.error(f"Error updating ve_allocate list: {str(e)}.")
            time.sleep(self._monitor_sleep_time)

    def thread_process_purgatory(self):
        while True:
            if self._thread_process_purgatory_is_on:
                logger.info("Starting purgatory.update_lists ....")
                try:
                    self.purgatory.update_lists()
                except (KeyError, Exception) as e:
                    logger.error(f"Error updating purgatory list: {str(e)}.")
            time.sleep(self._monitor_sleep_time)

    # various functions used by threads
    def process_current_blocks(self):
        """Process all blocks from the last processed block to the current block."""

        last_block = self.get_last_processed_block()
        current_block = None
        try:
            current_block = self._web3.eth.block_number
        except (KeyError, Exception) as e:
            logger.error(f"Failed to get web3.eth.block_number {str(e)}.")
            return
        if (
            not current_block
            or not isinstance(current_block, int)
            or current_block <= last_block
        ):
            return

        from_block = last_block
        logger.debug(
            f"Web3 block:{current_block}, from:block {from_block}, chunk: {self.blockchain_chunk_size}"
        )
        start_block_chunk = from_block
        for end_block_chunk in range(
            from_block, current_block, self.blockchain_chunk_size
        ):
            self.process_block_range(start_block_chunk, end_block_chunk)
            start_block_chunk = end_block_chunk

        self.process_block_range(end_block_chunk, current_block)

    def process_block_range(self, from_block, to_block):
        """Process a range of blocks."""
        logger.debug(
            f"Metadata monitor (chain: {self._chain_id})>>>> from_block:{from_block}, current_block:{to_block} <<<<"
        )

        if from_block > to_block:
            return

        processor_args = [
            self._es_instance,
            self._web3,
            self._allowed_publishers,
            self.purgatory,
            self._chain_id,
        ]

        # event retrieval
        all_events = self.get_all_events(from_block, to_block)

        regular_event_processors = {
            EventTypes.EVENT_METADATA_CREATED: MetadataCreatedProcessor,
            EventTypes.EVENT_METADATA_UPDATED: MetadataUpdatedProcessor,
            EventTypes.EVENT_METADATA_STATE: MetadataStateProcessor,
        }

        # event handling
        for event_name, events_to_process in all_events.items():
            if event_name == EventTypes.EVENT_TRANSFER:
                logger.debug(
                    f"Starting handle_transfer_ownership for {len(events_to_process)} events"
                )
                self.handle_transfer_ownership(events_to_process)
            elif event_name in regular_event_processors.keys():
                logger.debug(
                    f"Starting handle_regular_event_processor for {len(events_to_process)} events"
                )
                self.handle_regular_event_processor(
                    event_name,
                    regular_event_processors[event_name],
                    processor_args,
                    events_to_process,
                )
            elif event_name in [
                EventTypes.EVENT_ORDER_STARTED,
                EventTypes.EVENT_EXCHANGE_CREATED,
                EventTypes.EVENT_EXCHANGE_RATE_CHANGED,
                EventTypes.EVENT_DISPENSER_CREATED,
            ]:
                logger.debug(
                    f"Starting handle_price_change for {len(events_to_process)} events"
                )
                self.handle_price_change(event_name, events_to_process, to_block)
            elif event_name == EventTypes.EVENT_TOKEN_URI_UPDATE:
                logger.debug(
                    f"Starting handle_token_uri_update for {len(events_to_process)} events"
                )
                self.handle_token_uri_update(events_to_process)
            else:
                logger.warning(f"Unknown event {event_name}")
                logger.warning(events_to_process)
        self.store_last_processed_block(to_block)

    def get_all_events(self, from_block, to_block):
        logger.debug(
            f"**************Getting all events between {from_block} to {to_block}"
        )
        all_events = {
            EventTypes.EVENT_TRANSFER: [],
            # "regular" events
            EventTypes.EVENT_METADATA_CREATED: [],
            EventTypes.EVENT_METADATA_UPDATED: [],
            EventTypes.EVENT_METADATA_STATE: [],
            # price changed events
            EventTypes.EVENT_ORDER_STARTED: [],
            EventTypes.EVENT_EXCHANGE_CREATED: [],
            EventTypes.EVENT_EXCHANGE_RATE_CHANGED: [],
            EventTypes.EVENT_DISPENSER_CREATED: [],
            #
            EventTypes.EVENT_TOKEN_URI_UPDATE: [],
        }

        if from_block >= to_block:
            return all_events

        try:
            for event_name in all_events.keys():
                all_events[event_name] = self.get_event_logs(
                    event_name, from_block, to_block
                )

            return all_events
        except Exception:
            logger.info(f"Failed to get events from {from_block} to {to_block}")
            middle = int((from_block + to_block) / 2)
            middle_plus = middle + 1
            logger.info(
                f"Splitting in two:  {from_block} -> {middle} and {middle_plus} to {to_block}"
            )
            return merge_list_dictionary(
                self.get_all_events(from_block, middle),
                self.get_all_events(middle_plus, to_block),
            )

    def handle_regular_event_processor(
        self, event_name, processor, processor_args, events
    ):
        """Process emitted events between two given blocks for a given event name.

        Args:
            event_name (str): event uppercase constant name
            processor (EventProcessor): event processor
            processor_args (List[any]): list of processors arguments
            from_block (int): inital block
            to_block (int): final block
        """
        for event in events:
            dt_contract = self._web3.eth.contract(
                abi=ERC721Template.abi,
                address=self._web3.toChecksumAddress(event.address),
            )
            receipt = self._web3.eth.get_transaction_receipt(
                event.transactionHash.hex()
            )
            event_object = dt_contract.events[event_name]().processReceipt(
                receipt, errors=DISCARD
            )[0]
            try:
                metadata_proofs = dt_contract.events.MetadataValidated().processReceipt(
                    receipt, errors=DISCARD
                )
                event_processor = processor(
                    *([event_object, dt_contract, receipt["from"]] + processor_args)
                )
                event_processor.metadata_proofs = metadata_proofs
                event_processor.process()
            except Exception as e:
                self.retry_mechanism.add_to_retry_queue(
                    event.transactionHash.hex(), 0, processor_args[4]
                )
                logger.exception(
                    f"Error processing {event_name} event: {e}\n" f"event={event}"
                )

    def handle_price_change(self, event_name, events, to_block):
        for event in events:
            receipt = self._web3.eth.get_transaction_receipt(
                event.transactionHash.hex()
            )
            erc20_address = None
            if event_name == EventTypes.EVENT_EXCHANGE_CREATED:
                if is_approved_fre(self._web3, event.address, self._chain_id):
                    fre = get_fre(self._web3, self._chain_id, event.address)
                    exchange_id = (
                        fre.events.ExchangeCreated()
                        .processReceipt(receipt)[0]
                        .args.exchangeId
                    )
                    try:
                        erc20_address = fre.caller.getExchange(exchange_id)[1]
                    except Exception as e:
                        logger.warning(
                            f"Failed to get ERC20 address for {exchange_id} on fre: {event.address}:  {e}"
                        )
                    logger.debug(f"Erc20Addr:{erc20_address}")
                else:
                    logger.debug(
                        f"Event {event_name} detected on unapproved fre {event.address}"
                    )
            elif event_name == EventTypes.EVENT_EXCHANGE_RATE_CHANGED:
                if is_approved_fre(self._web3, event.address, self._chain_id):
                    fre = get_fre(self._web3, self._chain_id)
                    exchange_id = (
                        fre.events.ExchangeRateChanged()
                        .processReceipt(receipt)[0]
                        .args.exchangeId
                    )
                    try:
                        erc20_address = fre.caller.getExchange(exchange_id)[1]
                    except Exception as e:
                        logger.warning(
                            f"Failed to get ERC20 address for {exchange_id} on fre: {event.address}:  {e}"
                        )
                else:
                    logger.debug(
                        f"Event {event_name} detected on unapproved fre {event.address}"
                    )
            elif event_name == EventTypes.EVENT_DISPENSER_CREATED:
                if is_approved_dispenser(self._web3, event.address, self._chain_id):
                    dispenser = get_dispenser(self._web3, self._chain_id)
                    erc20_address = (
                        dispenser.events.DispenserCreated()
                        .processReceipt(receipt)[0]
                        .args.datatokenAddress
                    )
                else:
                    logger.debug(
                        f"Event {event_name} detected on unapproved dispenser {event.address}"
                    )
            else:
                erc20_address = event.address
            if erc20_address is None:
                return
            erc20_contract = self._web3.eth.contract(
                abi=ERC20Template.abi,
                address=self._web3.toChecksumAddress(erc20_address),
            )

            logger.debug(f"{event_name} detected on ERC20 contract {event.address}.")

            try:
                event_processor = OrderStartedProcessor(
                    erc20_contract.caller.getERC721Address(),
                    self._es_instance,
                    to_block,
                    self._chain_id,
                )
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing {event_name} event: {e}\n" f"event={event}"
                )

    def handle_token_uri_update(self, events):
        for event in events:
            try:
                event_processor = TokenURIUpdatedProcessor(
                    event, self._web3, self._es_instance, self._chain_id
                )
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing token update event: {e}\n" f"event={event}"
                )

    def handle_transfer_ownership(self, events):
        for event in events:
            try:
                event_processor = TransferProcessor(
                    event, self._web3, self._es_instance, self._chain_id
                )
                if event_processor.asset is not None:
                    event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing token transfer event: {e}\n" f"event={event}"
                )

    def get_last_processed_block(self):
        block = get_defined_block(self._chain_id)
        try:
            # Re-establishing the connection with ES
            while True:
                try:
                    if self._es_instance.es.ping() is True:
                        break
                except elasticsearch.exceptions.ElasticsearchException as es_err:
                    logging.error(f"Elasticsearch error: {es_err}")
                logging.error("Connection to ES failed. Trying to connect to back...")
                time.sleep(5)
            logging.info("Stable connection to ES.")
            last_block_record = self._es_instance.es.get(
                index=self._other_db_index, id=self._index_name, doc_type="_doc"
            )["_source"]
            block = (
                last_block_record["last_block"]
                if last_block_record["last_block"] >= 0
                else get_defined_block(self._chain_id)
            )
        except Exception as e:
            # Retrieve the defined block.
            if type(e) == elasticsearch.NotFoundError:
                block = get_defined_block(self._chain_id)
                logger.info(f"Retrieved the default block. NotFound error occurred.")
            else:
                logging.error(f"Cannot get last_block error={e}")
        return block

    def store_last_processed_block(self, block):
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        logger.debug(f"Storing last_processed_block {block}  (In Es: {stored_block})")
        if block <= stored_block:
            return
        record = {"last_block": block, "version": get_version()}
        try:
            self._es_instance.es.index(
                index=self._other_db_index,
                id=self._index_name,
                body=record,
                doc_type="_doc",
                refresh="wait_for",
            )["_id"]

        except elasticsearch.exceptions.RequestError:
            logger.error(
                f"store_last_processed_block: block={block} type={type(block)}, ES RequestError"
            )

    def add_chain_id_to_chains_list(self):
        try:
            chains = self._es_instance.es.get(
                index=self._other_db_index, id="chains", doc_type="_doc"
            )["_source"]
        except Exception:
            chains = dict()
        chains[str(self._chain_id)] = True

        try:
            self._es_instance.es.index(
                index=self._other_db_index,
                id="chains",
                body=json.dumps(chains),
                doc_type="_doc",
                refresh="wait_for",
            )["_id"]
            logger.info(f"Added {self._chain_id} to chains list")
        except elasticsearch.exceptions.RequestError:
            logger.error(
                f"Cannot add chain_id {self._chain_id} to chains list: ES RequestError"
            )

    def reset_chain(self):
        assets = self.get_assets_in_chain()
        for asset in assets:
            try:
                self._es_instance.delete(asset["id"])
            except Exception as e:
                logging.error(f"Delete asset failed: {str(e)}")

        self.store_last_processed_block(self._start_block)

    def get_assets_in_chain(self):
        body = {
            "query": {
                "query_string": {"query": self._chain_id, "default_field": "chainId"}
            }
        }
        page = self._es_instance.es.search(index=self._es_instance.db_index, body=body)
        total = page["hits"]["total"]["value"]
        body["size"] = total
        page = self._es_instance.es.search(index=self._es_instance.db_index, body=body)

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        return object_list

    def get_event_logs(self, event_name, from_block, to_block, chunk_size=1000):
        if event_name not in EventTypes.get_all_values():
            return []

        if event_name == EventTypes.EVENT_METADATA_CREATED:
            hash_text = "MetadataCreated(address,uint8,string,bytes,bytes,bytes32,uint256,uint256)"
        elif event_name == EventTypes.EVENT_METADATA_UPDATED:
            hash_text = "MetadataUpdated(address,uint8,string,bytes,bytes,bytes32,uint256,uint256)"
        elif event_name == EventTypes.EVENT_METADATA_STATE:
            hash_text = "MetadataState(address,uint8,uint256,uint256)"
        elif event_name == EventTypes.EVENT_TOKEN_URI_UPDATE:
            hash_text = "TokenURIUpdate(address,string,uint256,uint256,uint256)"
        elif event_name == EventTypes.EVENT_EXCHANGE_CREATED:
            hash_text = "ExchangeCreated(bytes32,address,address,address,uint256)"
        elif event_name == EventTypes.EVENT_EXCHANGE_RATE_CHANGED:
            hash_text = "ExchangeRateChanged(bytes32,address,uint256)"
        elif event_name == EventTypes.EVENT_DISPENSER_CREATED:
            hash_text = "DispenserCreated(address,address,uint256,uint256,address)"
        elif event_name == EventTypes.EVENT_TRANSFER:
            hash_text = "Transfer(address,address,uint256)"
        else:
            hash_text = (
                "OrderStarted(address,address,uint256,uint256,uint256,address,uint256)"
            )

        event_signature_hash = self._web3.keccak(text=hash_text).hex()

        _from = from_block
        _to = min(_from + chunk_size - 1, to_block)

        logger.debug(
            f"Searching for {event_name} events on chain {self._chain_id} "
            f"in blocks {from_block} to {to_block}."
        )

        filter_params = {
            "topics": [event_signature_hash],
            "fromBlock": _from,
            "toBlock": _to,
        }

        all_logs = []
        while _from <= to_block:
            # Search current chunk
            logs = self._web3.eth.get_logs(filter_params)
            all_logs.extend(logs)
            if (_from - from_block) % 1000 == 0:
                logger.debug(
                    f"Searched blocks {_from} to {_to} on chain {self._chain_id}; "
                    f"{len(all_logs)} {event_name} events detected so far."
                )

            # Prepare for next chunk
            _from = _to + 1
            _to = min(_from + chunk_size - 1, to_block)
            filter_params.update({"fromBlock": _from, "toBlock": _to})

        logger.info(
            f"Finished searching for {event_name} events on chain {self._chain_id} "
            f"in blocks {from_block} to {to_block}. "
            f"{len(all_logs)} {event_name} events detected."
        )

        return all_logs


def merge_list_dictionary(dict_1, dict_2):
    dict_3 = {**dict_1, **dict_2}
    for key, value in dict_3.items():
        if key in dict_1 and key in dict_2:
            dict_3[key] = value + dict_1[key]

    return dict_3
