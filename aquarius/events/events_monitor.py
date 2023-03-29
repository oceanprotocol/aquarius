#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from distutils.util import strtobool
from threading import Thread

import elasticsearch

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import get_bool_env_value, get_allowed_publishers
from aquarius.block_utils import BlockProcessingClass
from aquarius.config import get_version
from aquarius.retry_mechanism import RetryMechanism
from aquarius.events.constants import EventTypes
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataStateProcessor,
    MetadataUpdatedProcessor,
    OrderStartedProcessor,
    TokenURIUpdatedProcessor,
)
from aquarius.events.purgatory import Purgatory
from aquarius.events.ve_allocate import VeAllocate
from aquarius.events.nft_ownership import NftOwnership
from aquarius.events.util import (
    get_metadata_start_block,
    get_defined_block,
    get_fre,
    get_dispenser,
    get_erc20_contract,
    get_nft_contract,
    is_approved_fre,
    is_approved_dispenser,
)
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

    def __init__(self, web3):
        self._es_instance = ElasticsearchInstance()

        self._other_db_index = f"{self._es_instance.db_index}_plus"
        self._es_instance.es.indices.create(index=self._other_db_index, ignore=400)

        self._retries_db_index = f"{self._es_instance.db_index}_retries"
        self._es_instance.es.indices.create(index=self._retries_db_index, ignore=400)

        self._nfts_db_index = f"{self._es_instance.db_index}_nfts"
        self._es_instance.es.indices.create(index=self._nfts_db_index, ignore=400)

        self._web3 = web3

        self._chain_id = self._web3.eth.chain_id
        self.add_chain_id_to_chains_list()
        self._index_name = "events_last_block_" + str(self._chain_id)
        self._start_block = get_metadata_start_block()

        if get_bool_env_value("EVENTS_CLEAN_START", 0):
            self.reset_chain()

        self.get_or_set_last_block()
        self._allowed_publishers = get_allowed_publishers()
        logger.info(f"allowed publishers: {self._allowed_publishers}")

        # get timers
        self._monitor_sleep_time = self.get_timer_with_default(
            "EVENTS_MONITOR_SLEEP_TIME", 30
        )

        self._process_queue_sleep_time = self.get_timer_with_default(
            "EVENTS_PROCESS_QUEUE_SLEEP_TIME", 60
        )
        self._ve_allocate_sleep_time = self.get_timer_with_default(
            "EVENTS_VE_ALLOCATE_SLEEP_TIME", 300
        )
        self._nft_transfer_sleep_time = self.get_timer_with_default(
            "EVENTS_NFT_TRANSFER_SLEEP_TIME", 300
        )
        self._purgatory_sleep_time = self.get_timer_with_default(
            "EVENTS_PURGATORY_SLEEP_TIME", 300
        )
        logger.info(
            " Timers set to:\n"
            + f"\tEVENTS_MONITOR_SLEEP_TIME:{self._monitor_sleep_time}\n"
            + f"\tEVENTS_PROCESS_QUEUE_SLEEP_TIME:{self._process_queue_sleep_time}\n"
            + f"\tEVENTS_VE_ALLOCATE_SLEEP_TIME:{self._ve_allocate_sleep_time}\n"
            + f"\tEVENTS_NFT_TRANSFER_SLEEP_TIME:{self._nft_transfer_sleep_time}\n"
            + f"\tEVENTS_PURGATORY_SLEEP_TIME:{self._purgatory_sleep_time}\n"
        )

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
            self._es_instance,
            self._retries_db_index,
            self.purgatory,
            self._chain_id,
            self,
        )
        self.nft_ownership = NftOwnership(
            self._es_instance, self._nfts_db_index, self._chain_id, self
        )

        purgatory_message = (
            "Purgatory enabled" if self.purgatory else "Purgatory disabled"
        )
        logger.info(purgatory_message)
        self._thread_process_blocks_is_on = False
        self._thread_process_queue_is_on = False
        self._thread_process_ve_allocate_is_on = False
        self._thread_process_purgatory_is_on = False
        self._thread_process_nfts_is_on = False

    @property
    def block_envvar(self):
        return "METADATA_CONTRACT_BLOCK"

    def get_timer_with_default(self, env_name, default_value):
        """Gets a timer values from ENV or default value."""
        try:
            timer_value = int(os.getenv(env_name, default_value))
        except ValueError:
            timer_value = default_value
        return timer_value

    def stop_monitor(self):
        """Stops all threads for processing more data"""
        self._thread_process_blocks_is_on = False
        self._thread_process_queue_is_on = False
        self._thread_process_ve_allocate_is_on = False
        self._thread_process_purgatory_is_on = False
        self._thread_process_nfts_is_on = False

    def start_events_monitor(self):
        """Starts all needed threads, depending on config"""
        logger.info("Starting the threads..")
        t = Thread(target=self.thread_process_blocks, daemon=True)
        self._thread_process_blocks_is_on = True
        t.start()

        t = Thread(target=self.thread_process_nft_ownership, daemon=True)
        self._thread_process_nfts_is_on = True
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
            time.sleep(self._process_queue_sleep_time)

    def thread_process_ve_allocate(self):
        while True:
            if self._thread_process_ve_allocate_is_on:
                logger.info("Starting ve_allocate.update_lists ....")
                try:
                    self.ve_allocate.update_lists()
                except (KeyError, Exception) as e:
                    logger.error(f"Error updating ve_allocate list: {str(e)}.")
            time.sleep(self._ve_allocate_sleep_time)

    def thread_process_nft_ownership(self):
        while True:
            if self._thread_process_nfts_is_on:
                logger.info("Starting nft_ownership update_lists ....")
                try:
                    self.nft_ownership.update_lists()
                except (KeyError, Exception) as e:
                    logger.error(f"Error updating nft ownerships: {str(e)}.")
            time.sleep(self._nft_transfer_sleep_time)

    def thread_process_purgatory(self):
        while True:
            if self._thread_process_purgatory_is_on:
                logger.info("Starting purgatory.update_lists ....")
                try:
                    self.purgatory.update_lists()
                except (KeyError, Exception) as e:
                    logger.error(f"Error updating purgatory list: {str(e)}.")
            time.sleep(self._purgatory_sleep_time)

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

        from_block = (
            last_block + 1
        )  # we don't need to process last block again, it's a waste of rpc
        logger.debug(
            f"Web3 block:{current_block}, from:block {from_block}, chunk: {self.blockchain_chunk_size}"
        )
        if from_block > current_block:
            # nothing to do for now
            return
        start_block_chunk = from_block
        steps = range(from_block, current_block, self.blockchain_chunk_size)
        # if we only have one step, it will be processed at line #228 anyway
        if len(steps) > 1:
            for end_block_chunk in steps:
                self.process_block_range(start_block_chunk, end_block_chunk)
                start_block_chunk = end_block_chunk
        else:
            end_block_chunk = start_block_chunk
        self.process_block_range(end_block_chunk, current_block)

    def process_block_range(self, from_block, to_block):
        """Process a range of blocks.
        If fails, and possible, try to split the chunk in two and try again
        """
        if from_block > to_block:
            return

        try:
            self.get_and_process_logs(from_block, to_block)

        except Exception as e:
            logger.info(f"Failed to get events from {from_block} to {to_block}")
            # if we can split it in two, just do it
            if from_block < to_block:
                middle = int((from_block + to_block) / 2)
                middle_plus = middle + 1
                logger.info(
                    f"Splitting in two:  {from_block} -> {middle} and {middle_plus} to {to_block}"
                )
                self.process_block_range(from_block, middle)
                self.process_block_range(middle_plus, to_block)
            else:
                # so we failed to process a single block.
                self.retry_mechanism.add_block_to_retry_queue(from_block)
                logger.error(
                    f"Failed to get some events from block {from_block}. Error: {e}"
                )
            return

    def handle_metadata_updates(self, event_name, processor_args, event):
        """Process one event of types EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED, EVENT_METADATA_STATE

        Args:
            event_name (str): event uppercase constant name
            processor_args (List[any]): list of processors arguments
            event: event to be processed
        """
        processor = None
        if event_name == EventTypes.EVENT_METADATA_CREATED:
            processor = MetadataCreatedProcessor
        elif event_name == EventTypes.EVENT_METADATA_UPDATED:
            processor = MetadataUpdatedProcessor
        elif event_name == EventTypes.EVENT_METADATA_STATE:
            processor = MetadataStateProcessor
        if not processor:
            # unkown type of event, bail out
            return

        dt_contract = get_nft_contract(self._web3, event.address)
        receipt = self._web3.eth.get_transaction_receipt(event.transactionHash.hex())
        event_object = dt_contract.events[event_name]().process_receipt(
            receipt, errors=DISCARD
        )[0]
        try:
            metadata_proofs = dt_contract.events.MetadataValidated().process_receipt(
                receipt, errors=DISCARD
            )
            event_processor = processor(
                *([event_object, dt_contract, receipt["from"]] + processor_args)
            )
            event_processor.metadata_proofs = metadata_proofs
            event_processor.process()
        except Exception as e:
            error = f"Error processing {event_name} event: {e}\n" f"event={event}"
            logger.exception(error)
            self.retry_mechanism.add_event_to_retry_queue(event, event.address, error)

    def handle_price_change(self, event_name, event, to_block):
        """Process one event of types: EVENT_ORDER_STARTED, EVENT_EXCHANGE_CREATED, EVENT_EXCHANGE_RATE_CHANGED, EVENT_DISPENSER_CREATED

        Args:
            event_name (str): event uppercase constant name
            event: event to be processed
            to_block: last block in the current queue
        """
        receipt = self._web3.eth.get_transaction_receipt(event.transactionHash.hex())
        erc20_address = None
        if event_name == EventTypes.EVENT_EXCHANGE_CREATED:
            if is_approved_fre(self._web3, event.address, self._chain_id):
                fre = get_fre(self._web3, self._chain_id, event.address)
                exchange_id = (
                    fre.events.ExchangeCreated()
                    .process_receipt(receipt, errors=DISCARD)[0]
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
                    .process_receipt(receipt, errors=DISCARD)[0]
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
                    .process_receipt(receipt, errors=DISCARD)[0]
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

        erc20_contract = get_erc20_contract(self._web3, erc20_address)
        nft_address = erc20_contract.caller.getERC721Address()
        logger.debug(f"{event_name} detected on ERC20 contract {event.address}.")

        try:
            event_processor = OrderStartedProcessor(
                nft_address,
                self._es_instance,
                to_block,
                self._chain_id,
            )
            event_processor.process()
        except Exception as e:
            error = f"Error processing {event_name} event: {e}\n" f"event={event}"
            logger.error(error)
            self.retry_mechanism.add_event_to_retry_queue(event, nft_address, error)

    def handle_token_uri_update(self, event):
        """Process one token uri update event

        Args:
            event: event to be processed
        """
        try:
            event_processor = TokenURIUpdatedProcessor(
                event, self._web3, self._es_instance, self._chain_id
            )
            event_processor.process()
        except Exception as e:
            error = f"Error processing token update event: {e}\n" f"event={event}"
            logger.error(error)
            self.retry_mechanism.add_event_to_retry_queue(event, event.address, error)

    def get_last_processed_block(self):
        """Get last processed_block, fallback to contract deployment block"""
        block = get_defined_block(self._chain_id)
        try:
            # Re-establishing the connection with ES
            while True:
                try:
                    if self._es_instance.es.ping() is True:
                        break
                except Exception as es_err:
                    logging.error(f"Elasticsearch error: {es_err}")
                logging.error("Connection to ES failed. Trying to connect to back...")
                time.sleep(5)
            # logging.info("Stable connection to ES.")
            last_block_record = self._es_instance.es.get(
                index=self._other_db_index, id=self._index_name
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
        """Stores last processed block

        Args:
            block: last block that was processed
        """
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        logger.info(f"Storing last_processed_block {block}  (In Es: {stored_block})")
        if block <= stored_block:
            return
        record = {"last_block": block, "version": get_version()}
        try:
            self._es_instance.es.index(
                index=self._other_db_index,
                id=self._index_name,
                body=record,
                refresh="wait_for",
            )["_id"]

        except elasticsearch.exceptions.RequestError:
            logger.error(
                f"store_last_processed_block: block={block} type={type(block)}, ES RequestError"
            )

    def add_chain_id_to_chains_list(self):
        try:
            chains = self._es_instance.es.get(index=self._other_db_index, id="chains")[
                "_source"
            ]
        except Exception:
            chains = dict()
        chains[str(self._chain_id)] = True

        try:
            self._es_instance.es.index(
                index=self._other_db_index,
                id="chains",
                body=json.dumps(chains),
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
        query = {"query_string": {"query": self._chain_id, "default_field": "chainId"}}

        page = self._es_instance.es.search(
            index=self._es_instance.db_index, query=query
        )
        total = page["hits"]["total"]["value"]
        page = self._es_instance.es.search(
            index=self._es_instance.db_index, query=query, size=total
        )

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        return object_list

    def get_and_process_event_logs_for_one_block(self, block):
        """Get events for one topic at a time from one block -> multiple rpc calls

        Args:
            block: block to index
        """
        for topic in EventTypes.hashes:
            filter_params = {
                "topics": [topic],
                "fromBlock": block,
                "toBlock": block,
            }
            try:
                logs = self._web3.eth.get_logs(filter_params)
                self.process_logs(logs, block)
            except Exception as e:
                logger.error(
                    f"Failed to fetch {EventTypes.hashes[topic]['type']} logs from block {block}. {e}"
                )
        return

    def get_and_process_logs(self, from_block, to_block):
        """Get all events from -> to in a single call and process them.
        If that fails, and we tried with multiple blocks, let split handle it
        If that fails, and we tried on a single block, then try to get events one by one instead of all

        Args:
            from_block: first block in chunk
            to_block: last block in chunk
        """
        logger.info(
            f"Searching for events events on chain {self._chain_id} "
            f"in blocks {from_block} to {to_block}."
        )

        filter_params = {
            "topics": [list(EventTypes.hashes.keys())],
            "fromBlock": from_block,
            "toBlock": to_block,
        }

        try:
            logs = self._web3.eth.get_logs(filter_params)
        except Exception as e:
            if from_block < to_block:
                # splitting in two might help, so rely on that
                raise Exception("Failed to get events for multiple blocks. {e}")
            else:
                # Since there is only one block, and we failed to get all events, we need to try to take them one by one
                # if any call fails, there is nothing more we can do  (ie:  failed to get only transfer events from block X)
                self.get_and_process_event_logs_for_one_block(from_block)
                return
        try:
            self.process_logs(logs, to_block)
        except Exception as e:
            logger.error(
                f"Failed to process logs {from_block} to {to_block}. Error: {e}"
            )
        # finally, stored last block in ES
        self.store_last_processed_block(to_block)

    def process_logs(self, logs, to_block):
        """Given a list of events, of different types, process them ..

        Args:
            logs: list of events to be processed
            to_block: last block in the queue
        """
        processor_args = [
            self._es_instance,
            self._web3,
            self._allowed_publishers,
            self.purgatory,
            self._chain_id,
        ]

        logger.info(f"Processing {len(logs)} events ...")
        for event in logs:
            match = EventTypes.hashes.get(event.topics[0].hex(), None)
            if match is None:
                logger.warning(f"Unknown event ")
                logger.warning(event)
                continue
            if (
                match["type"] == EventTypes.EVENT_METADATA_CREATED
                or match["type"] == EventTypes.EVENT_METADATA_UPDATED
                or match["type"] == EventTypes.EVENT_METADATA_STATE
            ):
                self.handle_metadata_updates(
                    match["type"],
                    processor_args,
                    event,
                )
            elif match["type"] in [
                EventTypes.EVENT_ORDER_STARTED,
                EventTypes.EVENT_EXCHANGE_CREATED,
                EventTypes.EVENT_EXCHANGE_RATE_CHANGED,
                EventTypes.EVENT_DISPENSER_CREATED,
            ]:
                self.handle_price_change(match["type"], event, to_block)
            elif match["type"] == EventTypes.EVENT_TOKEN_URI_UPDATE:
                self.handle_token_uri_update(event)

        return


def merge_list_dictionary(dict_1, dict_2):
    dict_3 = {**dict_1, **dict_2}
    for key, value in dict_3.items():
        if key in dict_1 and key in dict_2:
            dict_3[key] = value + dict_1[key]

    return dict_3
