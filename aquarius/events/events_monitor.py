#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import lzma as Lzma
import os
import time
from datetime import datetime
from json import JSONDecodeError
from threading import Thread

import ecies
import elasticsearch
import eth_keys
import requests
from eth_account import Account
from eth_utils import add_0x_prefix, remove_0x_prefix
from ocean_lib.config_provider import ConfigProvider
from oceandb_driver_interface import OceanDb
from plecos.plecos import is_valid_dict_remote, list_errors_dict_remote

from aquarius.app.auth_util import compare_eth_addresses, sanitize_addresses
from aquarius.app.util import (
    DATETIME_FORMAT,
    format_timestamp,
    get_bool_env_value,
    get_metadata_from_services,
    init_new_ddo,
    list_errors,
    validate_data,
)
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.metadata_updater import MetadataUpdater
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
        if get_bool_env_value("PROCESS_POOL_EVENTS", 1):
            self._pool_monitor = MetadataUpdater(
                self._oceandb,
                self._other_db_index,
                self._web3,
                ConfigProvider.get_config(),
            )

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
        first_update = bool(
            self._pool_monitor and self._pool_monitor.is_first_update_enabled()
        )
        if self._purgatory_enabled:
            self._update_existing_assets_purgatory_data()

        while True:
            try:
                if not self._monitor_is_on:
                    return

                self.process_current_blocks()
                self._process_pool_events(first_update)
                first_update = False

                if self._purgatory_enabled:
                    self._update_purgatory_list()

            except (KeyError, Exception) as e:
                logger.error("Error processing event:")
                logger.error(e)

            time.sleep(self._monitor_sleep_time)

    def _process_pool_events(self, first_update=False):
        if not self._pool_monitor:
            return

        if first_update:
            self._pool_monitor.do_update()

        self._pool_monitor.process_pool_events()

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
        """Process all blocks from the last processed block to the current block."""
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

        start_block_chunk = from_block
        for end_block_chunk in range(from_block, current_block, 1000):
            self.process_block_range(start_block_chunk, end_block_chunk)
            start_block_chunk = end_block_chunk

        # Process last few blocks because range(start, end) doesn't include end
        self.process_block_range(end_block_chunk, current_block)

    def process_block_range(self, from_block, to_block):
        """Process a range of blocks."""
        if from_block >= to_block:
            return

        for event in self.get_event_logs(EVENT_METADATA_CREATED, from_block, to_block):
            try:
                self.processNewDDO(event)
            except Exception as e:
                logger.error(
                    f"Error processing new metadata event: {e}\n" f"event={event}"
                )

        for event in self.get_event_logs(EVENT_METADATA_UPDATED, from_block, to_block):
            try:
                self.processUpdateDDO(event)
            except Exception as e:
                logger.error(
                    f"Error processing update metadata event: {e}\n" f"event={event}"
                )

        self.store_last_processed_block(to_block)

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

    def is_publisher_allowed(self, publisher_address):
        logger.debug(f"checking allowed publishers: {publisher_address}")
        if not self._allowed_publishers:
            return True

        publisher_address = self._web3.toChecksumAddress(publisher_address)
        return publisher_address in self._allowed_publishers

    def processNewDDO(self, event):
        (
            did,
            block,
            txid,
            contract_address,
            sender_address,
            flags,
            rawddo,
            timestamp,
        ) = self.get_event_data(event)
        logger.info(
            f"Process new DDO, did from event log:{did}, sender:{sender_address}"
        )
        if not self.is_publisher_allowed(sender_address):
            logger.warning(f"Sender {sender_address} is not in ALLOWED_PUBLISHERS.")
            return

        try:
            self._oceandb.read(did)
            logger.warning(f"{did} is already registered")
            return
        except Exception:
            pass

        logger.info(f"Start processing {EVENT_METADATA_CREATED} event: did={did}")
        debug_log(
            f"block {block}, contract: {contract_address}, Sender: {sender_address} , txid: {txid}"
        )

        logger.debug(f"decoding with did {did} and flags {flags}")
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning(f"Could not decode ddo using flags {flags}")
            return

        msg, _ = validate_data(data, f"event {EVENT_METADATA_CREATED}")
        if msg:
            logger.warning(msg)
            return

        _record = init_new_ddo(data, timestamp)
        # this will be used when updating the doo
        _record["event"] = dict()
        _record["event"]["txid"] = txid
        _record["event"]["blockNo"] = block
        _record["event"]["from"] = sender_address
        _record["event"]["contract"] = contract_address

        _record["price"] = {
            "datatoken": 0.0,
            "ocean": 0.0,
            "value": 0.0,
            "type": "",
            "exchange_id": "",
            "address": "",
            "pools": [],
            "isConsumable": "",
        }
        dt_address = _record.get("dataToken")
        assert dt_address == add_0x_prefix(did[len("did:op:") :])
        if dt_address:
            _record["dataTokenInfo"] = get_datatoken_info(dt_address)

        if not is_valid_dict_remote(get_metadata_from_services(_record["service"])):
            errors = list_errors(
                list_errors_dict_remote, get_metadata_from_services(_record["service"])
            )
            logger.error(f"New ddo has validation errors: {errors}")
            return False

        _record["isInPurgatory"] = "false"

        try:
            record_str = json.dumps(_record)
            self._oceandb.write(record_str, did)
            _record = json.loads(record_str)
            name = _record["service"][0]["attributes"]["main"]["name"]
            debug_log(f"DDO saved: did={did}, name={name}, publisher={sender_address}")
            logger.info(
                f"Done processing {EVENT_METADATA_CREATED} event: did={did}. DDO SAVED TO DB"
            )
            return True
        except (KeyError, Exception) as err:
            logger.error(
                f"encountered an error while saving the asset data to OceanDB: {str(err)}"
            )
            return False

    def processUpdateDDO(self, event):
        (
            did,
            block,
            txid,
            contract_address,
            sender_address,
            flags,
            rawddo,
            timestamp,
        ) = self.get_event_data(event)
        debug_log(f"Process update DDO, did from event log:{did}")
        try:
            asset = self._oceandb.read(did)
        except Exception:
            # TODO: check if this asset was deleted/hidden due to some violation issues
            # if so, don't add it again
            logger.warning(f"{did} is not registered, will add it as a new DDO.")
            self.processNewDDO(event)
            return

        debug_log(
            f"block {block}, contract: {contract_address}, Sender: {sender_address} , txid: {txid}"
        )

        # do not update if we have the same txid
        ddo_txid = asset["event"]["txid"]
        if txid == ddo_txid:
            logger.warning(
                f'asset has the same txid, no need to update: event-txid={txid} <> asset-event-txid={asset["event"]["txid"]}'
            )
            return

        # check block
        ddo_block = asset["event"]["blockNo"]
        if int(block) <= int(ddo_block):
            logger.warning(
                f"asset was updated later (block: {ddo_block}) vs transaction block: {block}"
            )
            return

        # check owner
        if not compare_eth_addresses(
            asset["publicKey"][0]["owner"], sender_address, logger
        ):
            logger.warning("Transaction sender must mach ddo owner")
            return

        debug_log(f"decoding with did {did} and flags {flags}")
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning("Cound not decode ddo")
            return

        msg, _ = validate_data(data, "event update")
        if msg:
            logger.error(msg)
            return

        _record = init_new_ddo(data, timestamp)
        # make sure that we do not alter created flag
        _record["created"] = asset["created"]
        # but we update 'updated'
        _record["updated"] = format_timestamp(
            datetime.fromtimestamp(timestamp).strftime(DATETIME_FORMAT)
        )
        _record["event"] = dict()
        _record["event"]["txid"] = txid
        _record["event"]["blockNo"] = block
        _record["event"]["from"] = sender_address
        _record["event"]["contract"] = contract_address

        if not is_valid_dict_remote(get_metadata_from_services(_record["service"])):
            errors = list_errors(
                list_errors_dict_remote, get_metadata_from_services(_record["service"])
            )
            logger.error(f"ddo update has validation errors: {errors}")
            return

        _record["price"] = asset.get("price", {})
        dt_address = _record.get("dataToken")
        assert dt_address == add_0x_prefix(did[len("did:op:") :])
        if dt_address:
            _record["dataTokenInfo"] = get_datatoken_info(dt_address)

        _record["isInPurgatory"] = asset.get("isInPurgatory", "false")

        try:
            self._oceandb.update(json.dumps(_record), did)
            logger.info(f"updated DDO saved to db successfully (did={did}).")
            return True
        except (KeyError, Exception) as err:
            logger.error(
                f"encountered an error while updating the asset data to OceanDB: {str(err)}"
            )
            return

    def get_event_data(self, event):
        tx_id = event.transactionHash.hex()
        sender = event.args.get("createdBy", event.args.get("updatedBy"))
        blockInfo = self._web3.eth.getBlock(event.blockNumber)
        timestamp = blockInfo["timestamp"]
        return (
            f"did:op:{remove_0x_prefix(event.args.dataToken)}",
            event.blockNumber,
            tx_id,
            event.address,
            sender,
            event.args.get("flags", None),
            event.args.get("data", None),
            timestamp,
        )

    def decode_ddo(self, rawddo, flags):
        debug_log(f"flags: {flags}")
        # debug_log(f'Before unpack rawddo:{rawddo}')
        if len(flags) < 1:
            debug_log("Set check_flags to 0!")
            check_flags = 0
        else:
            check_flags = flags[0]
        if self._only_encrypted_ddo and (not check_flags & 2):
            logger.error("This aquarius can cache only encrypted ddos")
            return None
        # always start with MSB -> LSB
        debug_log(f"checkflags: {check_flags}")
        # bit 2:  check if ddo is ecies encrypted
        if check_flags & 2:
            try:
                rawddo = self.ecies_decrypt(rawddo)
                logger.debug(f"Decrypted to {rawddo}")
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decrypt: {str(err)}")

        # bit 1:  check if ddo is lzma compressed
        if check_flags & 1:
            try:
                rawddo = Lzma.decompress(rawddo)
                logger.debug(f"Decompressed to {rawddo}")
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decompress: {str(err)}")

        logger.debug(f"After unpack rawddo:{rawddo}")
        try:
            ddo = json.loads(rawddo)
            return ddo
        except (KeyError, Exception) as err:
            logger.error(f"encountered an error while decoding the ddo: {str(err)}")
            return None

    def ecies_decrypt(self, rawddo):
        if self._ecies_account is not None:
            key = eth_keys.KeyAPI.PrivateKey(self._ecies_account.privateKey)
            rawddo = ecies.decrypt(key.to_hex(), rawddo)
        return rawddo
