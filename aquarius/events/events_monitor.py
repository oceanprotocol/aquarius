#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from json import JSONDecodeError
from threading import Thread

import elasticsearch
from jsonsempai import magic  # noqa: F401

from aquarius.app.auth_util import sanitize_addresses
from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import get_bool_env_value
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.constants import EventTypes
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataStateProcessor,
    MetadataUpdatedProcessor,
    OrderStartedProcessor,
    TokenURIUpdatedProcessor,
)
from aquarius.events.purgatory import Purgatory
from aquarius.events.util import get_metadata_start_block
from artifacts import ERC20Template, ERC721Template

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

        self._web3 = web3

        self._chain_id = self._web3.eth.chain_id
        self.add_chain_id_to_chains_list()
        self._index_name = "events_last_block_" + str(self._chain_id)
        self._start_block = get_metadata_start_block()

        if get_bool_env_value("EVENTS_CLEAN_START", 0):
            self.reset_chain()

        self.get_or_set_last_block()
        allowed_publishers = set()
        try:
            publishers_str = os.getenv("ALLOWED_PUBLISHERS", "")
            allowed_publishers = (
                set(json.loads(publishers_str)) if publishers_str else set()
            )
        except (JSONDecodeError, TypeError, Exception) as e:
            logger.error(
                f"Reading list of allowed publishers failed: {e}\n"
                f"ALLOWED_PUBLISHERS is set to empty set."
            )

        self._allowed_publishers = set(sanitize_addresses(allowed_publishers))
        logger.debug(f"allowed publishers: {self._allowed_publishers}")

        self._monitor_is_on = False
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

        purgatory_message = (
            "Enabling purgatory" if self.purgatory else "Purgatory is disabled"
        )
        logger.info("PURGATORY: " + purgatory_message)

    @property
    def block_envvar(self):
        return "METADATA_CONTRACT_BLOCK"

    def start_events_monitor(self):
        if self._monitor_is_on:
            return

        logger.info("Starting the events monitor.")
        t = Thread(target=self.run_monitor, daemon=True)
        self._monitor_is_on = True
        t.start()

    def stop_monitor(self):
        self._monitor_is_on = False

    def run_monitor(self):
        while True:
            self.do_run_monitor()
            time.sleep(self._monitor_sleep_time)

    def do_run_monitor(self):
        if not self._monitor_is_on:
            return

        try:
            self.process_current_blocks()
        except (KeyError, Exception) as e:
            logger.error(f"Error processing event: {str(e)}.")

        if self.purgatory:
            try:
                self.purgatory.update_lists()
            except (KeyError, Exception) as e:
                logger.error(f"Error updating purgatory list: {str(e)}.")

    def process_current_blocks(self):
        """Process all blocks from the last processed block to the current block."""
        last_block = self.get_last_processed_block()
        current_block = self._web3.eth.block_number
        if (
            not current_block
            or not isinstance(current_block, int)
            or current_block <= last_block
        ):
            return

        from_block = last_block

        start_block_chunk = from_block
        for end_block_chunk in range(
            from_block, current_block, self.blockchain_chunk_size
        ):
            self.process_block_range(start_block_chunk, end_block_chunk)
            start_block_chunk = end_block_chunk

        # Process last few blocks because range(start, end) doesn't include end
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

        event_processors = {
            "EVENT_METADATA_CREATED": MetadataCreatedProcessor,
            "EVENT_METADATA_UPDATED": MetadataUpdatedProcessor,
            "EVENT_METADATA_STATE": MetadataStateProcessor,
        }
        for event_name in event_processors:
            self.handle_regular_event_processor(
                event_name,
                event_processors[event_name],
                processor_args,
                from_block,
                to_block,
            )

        self.handle_order_started(from_block, to_block)
        self.handle_token_uri_update(from_block, to_block)

        self.store_last_processed_block(to_block)

    def handle_regular_event_processor(
        self, event_name, processor, processor_args, from_block, to_block
    ):
        """Process emitted events between two given blocks for a given event name.

        Args:
            event_name (str): event uppercase constant name
            processor (EventProcessor): event processor
            processor_args (List[any]): list of processors arguments
            from_block (int): inital block
            to_block (int): final block
        """
        for event in self.get_event_logs(
            EventTypes.get_value(event_name), from_block, to_block
        ):
            dt_contract = self._web3.eth.contract(
                abi=ERC721Template.abi, address=event.address
            )
            receipt = self._web3.eth.get_transaction_receipt(
                event.transactionHash.hex()
            )
            event_object = dt_contract.events[
                EventTypes.get_value(event_name)
            ]().processReceipt(receipt)[0]
            try:
                event_processor = processor(
                    *([event_object, dt_contract, receipt["from"]] + processor_args)
                )
                event_processor.process()
            except Exception as e:
                logger.exception(
                    f"Error processing {EventTypes.get_value(event_name)} event: {e}\n"
                    f"event={event}"
                )

    def handle_order_started(self, from_block, to_block):
        events = self.get_event_logs(
            EventTypes.EVENT_ORDER_STARTED, from_block, to_block
        )

        for event in events:
            erc20_contract = self._web3.eth.contract(
                abi=ERC20Template.abi, address=event.address
            )

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
                    f"Error processing order started event: {e}\n" f"event={event}"
                )

    def handle_token_uri_update(self, from_block, to_block):
        events = self.get_event_logs(
            EventTypes.EVENT_TOKEN_URI_UPDATE, from_block, to_block
        )

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

    def get_last_processed_block(self):
        block = 0
        try:
            last_block_record = self._es_instance.es.get(
                index=self._other_db_index, id=self._index_name, doc_type="_doc"
            )["_source"]
            block = last_block_record["last_block"]
        except Exception as e:
            logger.error(f"Cannot get last_block error={e}")
        # no need to start from 0 if we have a deployment block
        if block < self._start_block:
            block = self._start_block
        return block

    def store_last_processed_block(self, block):
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        if block <= stored_block:
            return
        record = {"last_block": block}
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

        erc721_template_contract = self._web3.eth.contract(abi=ERC721Template.abi)
        erc20_template_contract = self._web3.eth.contract(abi=ERC20Template.abi)

        if event_name == EventTypes.EVENT_METADATA_CREATED:
            event = erc721_template_contract.events.MetadataCreated()
        elif event_name == EventTypes.EVENT_METADATA_UPDATED:
            event = erc721_template_contract.events.MetadataUpdated()
        elif event_name == EventTypes.EVENT_METADATA_STATE:
            event = erc721_template_contract.events.MetadataState()
        elif event_name == EventTypes.EVENT_TOKEN_URI_UPDATE:
            event = erc721_template_contract.events.TokenURIUpdate()
        else:
            event = erc20_template_contract.events.OrderStarted()

        _from = from_block
        _to = _from + chunk_size - 1

        all_logs = []
        _to = min(_to, to_block)
        while _from <= to_block:
            # Search current chunk
            logs = event.getLogs(fromBlock=_from, toBlock=_to)
            all_logs.extend(logs)
            if (_from - from_block) % 1000 == 0:
                logger.info(
                    f"Searched blocks {_from}-{_to}. {len(all_logs)} {event_name} events detected so far."
                )

            # Prepare for next chunk
            _from = _to + 1
            _to = min(_from + chunk_size - 1, to_block)

        return all_logs
