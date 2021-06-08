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
from eth_account import Account
from eth_utils import is_address
from oceandb_driver_interface import OceanDb

from aquarius.app.auth_util import sanitize_addresses
from aquarius.app.util import get_bool_env_value
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.purgatory import Purgatory
from aquarius.events.util import get_metadata_contract

logger = logging.getLogger(__name__)


class EventsMonitor(BlockProcessingClass):
    """Detect on-chain published Metadata and cache it in the database for
    fast retrieval and searchability.

    The published metadata is extracted from the `MetadataCreated`
    event log from the `Metadata` smartcontract. Metadata updates are also detected using
    the `MetadataUpdated` event.

    The Metadata json object is expected to be
    in an `lzma` compressed form. If desired the metadata can also be encrypted for specific
    use cases. When using encrypted Metadata, the EventsMonitor requires the private key of
    the ethereum account that is used for encryption. This can be specified in `EVENTS_ECIES_PRIVATE_KEY`
    envvar.

    The events monitor pauses for 25 seconds between updates.

    The cached Metadata can be restricted to only those published by specific ethereum accounts.
    To do this set the `ALLOWED_PUBLISHERS` envvar to the list of ethereum addresses of known publishers.



    """

    _instance = None

    def __init__(self, web3, config_file, metadata_contract=None):
        self._oceandb = OceanDb(config_file).plugin

        self._other_db_index = f"{self._oceandb.driver.db_index}_plus"
        self._oceandb.driver.es.indices.create(index=self._other_db_index, ignore=400)

        self._web3 = web3

        if not metadata_contract:
            metadata_contract = get_metadata_contract(self._web3)

        self._contract = metadata_contract
        self._contract_address = self._contract.address

        self._ecies_private_key = os.getenv("EVENTS_ECIES_PRIVATE_KEY", "")
        self._ecies_account = None
        if self._ecies_private_key:
            self._ecies_account = Account.from_key(self._ecies_private_key)
        self._only_encrypted_ddo = get_bool_env_value("ONLY_ENCRYPTED_DDO", 0)

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
                f'ALLOWED_PUBLISHER is set to "{os.getenv("ALLOWED_PUBLISHER")}"'
            )

        self._allowed_publishers = set(sanitize_addresses(allowed_publishers))
        logger.debug(f"allowed publishers: {self._allowed_publishers}")

        logger.debug(
            f"EventsMonitor: using Metadata contract address {self._contract_address}."
        )
        self._monitor_is_on = False
        default_sleep_time = 10
        try:
            self._monitor_sleep_time = int(
                os.getenv("OCN_EVENTS_MONITOR_QUITE_TIME", default_sleep_time)
            )
        except ValueError:
            self._monitor_sleep_time = default_sleep_time

        self._monitor_sleep_time = max(self._monitor_sleep_time, default_sleep_time)
        if not self._contract or not is_address(self._contract_address):
            logger.error(
                f"Contract address {self._contract_address} is not a valid address. Events thread not starting"
            )
            self._contract = None

        self.purgatory = (
            Purgatory(self._oceandb)
            if (os.getenv("ASSET_PURGATORY_URL") or os.getenv("ACCOUNT_PURGATORY_URL"))
            else None
        )

    @property
    def block_envvar(self):
        return "METADATA_CONTRACT_BLOCK"

    @property
    def is_monitor_running(self):
        return self._monitor_is_on

    def start_events_monitor(self):
        if self._monitor_is_on:
            return

        if self._contract_address is None:
            logger.error("Cannot start events monitor without a valid contract address")
            return

        if self._contract is None:
            logger.error("Cannot start events monitor without a valid contract object")
            return

        logger.info(
            f"Starting the events monitor on contract {self._contract_address}."
        )
        t = Thread(target=self.run_monitor, daemon=True)
        self._monitor_is_on = True
        t.start()

    def stop_monitor(self):
        self._monitor_is_on = False

    def run_monitor(self):
        if self.purgatory:
            self.purgatory.init_existing_assets()

        while True:
            try:
                if not self._monitor_is_on:
                    return

                self.process_current_blocks()

                if self.purgatory:
                    self.purgatory.update_lists()
            except (KeyError, Exception) as e:
                logger.error("Error processing event:")
                logger.error(e)

            time.sleep(self._monitor_sleep_time)

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
            f"Metadata monitor >>>> from_block:{from_block}, current_block:{to_block} <<<<"
        )

        if from_block > to_block:
            return

        processor_args = [
            self._oceandb,
            self._web3,
            self._ecies_account,
            self._allowed_publishers,
        ]

        for event in self.get_event_logs(EVENT_METADATA_CREATED, from_block, to_block):
            try:
                event_processor = MetadataCreatedProcessor(*([event] + processor_args))
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing new metadata event: {e}\n" f"event={event}"
                )

        for event in self.get_event_logs(EVENT_METADATA_UPDATED, from_block, to_block):
            try:
                event_processor = MetadataUpdatedProcessor(*([event] + processor_args))
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing update metadata event: {e}\n" f"event={event}"
                )

        self.store_last_processed_block(to_block)

    def get_last_processed_block(self):
        block = 0
        try:
            last_block_record = self._oceandb.driver.es.get(
                index=self._other_db_index, id="events_last_block", doc_type="_doc"
            )["_source"]
            block = last_block_record["last_block"]
        except Exception as e:
            logger.error(f"Cannot get last_block error={e}")
        # no need to start from 0 if we have a deployment block
        metadata_contract_block = int(os.getenv("METADATA_CONTRACT_BLOCK", 0))
        if block < metadata_contract_block:
            block = metadata_contract_block
        return block

    def store_last_processed_block(self, block):
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        if block <= stored_block:
            return
        record = {"last_block": block}
        try:
            self._oceandb.driver.es.index(
                index=self._other_db_index,
                id="events_last_block",
                body=record,
                doc_type="_doc",
                refresh="wait_for",
            )["_id"]

        except elasticsearch.exceptions.RequestError as e:
            logger.error(
                f"store_last_processed_block: block={block} type={type(block)}, error={e}"
            )

    def get_event_logs(self, event_name, from_block, to_block):
        def _get_logs(event, _from_block, _to_block):
            logger.debug(f"get_event_logs ({event_name}, {from_block}, {to_block})..")
            _filter = event().createFilter(fromBlock=_from_block, toBlock=_to_block)
            return _filter.get_all_entries()

        try:
            logs = _get_logs(
                getattr(self._contract.events, event_name), from_block, to_block
            )
            return logs
        except ValueError as e:
            logger.error(
                f"get_event_logs ({event_name}, {from_block}, {to_block}) failed: {e}.\n Retrying once more."
            )

        try:
            logs = _get_logs(
                getattr(self._contract.events, event_name), from_block, to_block
            )
            return logs
        except ValueError as e:
            logger.error(
                f"get_event_logs ({event_name}, {from_block}, {to_block}) failed: {e}."
            )
