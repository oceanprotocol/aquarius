#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from datetime import datetime
from json import JSONDecodeError
from threading import Thread

import elasticsearch
import requests
from eth_account import Account
from oceandb_driver_interface import OceanDb

from aquarius.app.auth_util import sanitize_addresses
from aquarius.app.util import get_bool_env_value
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.util import get_datatoken_info, get_metadata_contract

logger = logging.getLogger(__name__)

debug_log = logger.debug


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
        self._pool_monitor = None

        if not metadata_contract:
            metadata_contract = get_metadata_contract(self._web3)

        self._contract = metadata_contract
        self._contract_address = self._contract.address

        self._ecies_private_key = os.getenv("EVENTS_ECIES_PRIVATE_KEY", "")
        self._ecies_account = None
        if self._ecies_private_key:
            self._ecies_account = Account.privateKeyToAccount(self._ecies_private_key)
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
        if not self._contract or not self._web3.isAddress(self._contract_address):
            logger.error(
                f"Contract address {self._contract_address} is not a valid address. Events thread not starting"
            )
            self._contract = None
        self._purgatory_enabled = get_bool_env_value("PROCESS_PURGATORY", 1)
        self._purgatory_list = set()
        self._purgatory_update_time = None

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
        if self._pool_monitor and self._pool_monitor.is_running():
            self._pool_monitor.stop()

    def run_monitor(self):
        if self._purgatory_enabled:
            self._update_existing_assets_purgatory_data()

        while True:
            try:
                if not self._monitor_is_on:
                    return

                self.process_current_blocks()

                if self._purgatory_enabled:
                    self._update_purgatory_list()

            except (KeyError, Exception) as e:
                logger.error("Error processing event:")
                logger.error(e)

            time.sleep(self._monitor_sleep_time)

    def _update_existing_assets_purgatory_data(self):
        for asset in self._oceandb.list():
            did = asset.get("id", None)
            if not did or not did.startswith("did:op:"):
                continue

            purgatory = asset.get("isInPurgatory", "false")
            if not isinstance(purgatory, str):
                purgatory = "true" if purgatory is True else "false"

            asset["isInPurgatory"] = purgatory
            if "purgatoryData" in asset:
                asset.pop("purgatoryData")
            try:
                self._oceandb.update(json.dumps(asset), did)
            except Exception as e:
                logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    @staticmethod
    def _get_reference_purgatory_list():
        response = requests.get(
            "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
        )
        if response.status_code != requests.codes.ok:
            return set()

        return {(a["did"], a["reason"]) for a in response.json() if a and "did" in a}

    def _update_purgatory_list(self):
        now = int(datetime.now().timestamp())
        if self._purgatory_update_time and (now - self._purgatory_update_time) < 3600:
            return

        self._purgatory_update_time = now
        bad_list = self._get_reference_purgatory_list()
        if not bad_list:
            return

        if self._purgatory_list == bad_list:
            return

        new_ids = bad_list.difference(self._purgatory_list)
        self._purgatory_list = bad_list
        for _id, reason in new_ids:
            try:
                asset = self._oceandb.read(_id)
                asset["isInPurgatory"] = "true"
                if "purgatoryData" in asset:
                    asset.pop("purgatoryData")

                self._oceandb.update(json.dumps(asset), _id)

            except Exception:
                pass

    def process_current_blocks(self):
        try:
            last_block = self.get_last_processed_block()
        except Exception as e:
            debug_log(e)
            last_block = 0

        current_block = self._web3.eth.blockNumber
        if (
            not current_block
            or not isinstance(current_block, int)
            or current_block <= last_block
        ):
            return

        from_block = last_block
        debug_log(
            f"Metadata monitor >>>> from_block:{from_block}, current_block:{current_block} <<<<"
        )

        processor_args = [
            self._oceandb,
            self._web3,
            self._ecies_account,
            self._allowed_publishers,
        ]

        for event in self.get_event_logs(
            EVENT_METADATA_CREATED, from_block, current_block
        ):
            try:
                event_processor = MetadataCreatedProcessor(*([event] + processor_args))
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing new metadata event: {e}\n" f"event={event}"
                )

        for event in self.get_event_logs(
            EVENT_METADATA_UPDATED, from_block, current_block
        ):
            try:
                event_processor = MetadataUpdatedProcessor(*([event] + processor_args))
                event_processor.process()
            except Exception as e:
                logger.error(
                    f"Error processing update metadata event: {e}\n" f"event={event}"
                )

        self.store_last_processed_block(current_block)

    def get_last_processed_block(self):
        last_block_record = self._oceandb.driver.es.get(
            index=self._other_db_index, id="events_last_block", doc_type="_doc"
        )["_source"]
        return last_block_record["last_block"]

    def store_last_processed_block(self, block):
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
            debug_log(f"get_event_logs ({event_name}, {from_block}, {to_block})..")
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
