#  Copyright 2020 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import time
import lzma as Lzma
import json
from threading import Thread

from eth_utils import remove_0x_prefix
from web3 import Web3
from eth_account import Account
import eth_keys
import ecies
from oceandb_driver_interface import OceanDb

from aquarius.app.util import (
    get_timestamp,
    get_metadata_from_services,
    list_errors,
    validate_data,
    get_sender_from_txid,
    init_new_ddo)
from aquarius.app.auth_util import compare_eth_addresses
from plecos.plecos import (
    is_valid_dict_remote,
    list_errors_dict_remote,
)

from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.http_provider import CustomHTTPProvider

logger = logging.getLogger(__name__)

debug_log = logger.debug


def get_web3_connection_provider(network_url):
    if network_url.startswith('http'):
        provider = CustomHTTPProvider(network_url)
    else:
        assert network_url.startswith('ws'), f'network url must start with either https or wss'
        provider = Web3.WebsocketProvider(network_url)

    return provider


class EventsMonitor:
    _instance = None

    def __init__(self, rpc, metadata_contract, config_file):
        self._oceandb = OceanDb(config_file).plugin
        self._rpc = rpc

        self._web3 = Web3(get_web3_connection_provider(rpc))
        self._contract = metadata_contract
        self._contract_address = self._contract.address

        self._ecies_private_key = os.getenv('EVENTS_ECIES_PRIVATE_KEY', '')
        self._ecies_account = None
        if self._ecies_private_key:
            self._ecies_account = Account.from_key(self._ecies_private_key)

        print(f'EventsMonitor: using Metadata contact address {self._contract_address}, rpc {rpc}.')
        self._monitor_is_on = False
        try:
            self._monitor_sleep_time = os.getenv('OCN_EVENTS_MONITOR_QUITE_TIME', 3)
        except ValueError:
            self._monitor_sleep_time = 3

        self._monitor_sleep_time = max(self._monitor_sleep_time, 3)
        if not self._contract or not self._web3.isAddress(self._contract_address):
            logger.error(
                f"Contract address {self._contract_address} is not a valid address. Events thread not starting")
            self._contract = None
            return

    @property
    def is_monitor_running(self):
        return self._monitor_is_on

    def start_events_monitor(self):
        if self._monitor_is_on:
            return
        if self._contract_address is None:
            logger.error(
                'Cannot start events monitor without a valid contract address')
            return
        if self._contract is None:
            logger.error(
                'Cannot start events monitor without a valid contract object')
            return
        logger.info(
            f'Starting the events monitor on contract {self._contract_address}.')
        t = Thread(
            target=self.run_monitor,
            daemon=True,
        )
        self._monitor_is_on = True
        t.start()

    def stop_monitor(self):
        self._monitor_is_on = False

    def run_monitor(self):
        while True:
            try:
                if not self._monitor_is_on:
                    return

                self.process_current_blocks()

            except (KeyError, Exception) as e:
                logger.error(f'Error processing event:')
                logger.error(e)

            time.sleep(self._monitor_sleep_time)

    def process_current_blocks(self):
        current_block = self._web3.eth.blockNumber
        try:
            last_block = self.get_last_processed_block()
        except Exception as e:
            debug_log(e)
            last_block = 0

        debug_log(f'Last block:{last_block}, Current:{current_block}')
        last_block = min(last_block, current_block)
        for event in self.get_event_logs(EVENT_METADATA_CREATED, last_block, current_block):
            self.processNewDDO(event)

        for event in self.get_event_logs(EVENT_METADATA_UPDATED, last_block, current_block):
            self.processUpdateDDO(event)

        self.store_last_processed_block(current_block + 1)

    def get_last_processed_block(self):
        last_block_record = self._oceandb.read('events_last_block')
        last_block = last_block_record['last_block']
        return last_block

    def store_last_processed_block(self, block):
        record = {"last_block": block}
        self._oceandb.update(record, 'events_last_block')

    def get_event_logs(self, event_name, from_block, to_block):
        _filter = getattr(self._contract.events, event_name)().createFilter(
            fromBlock=from_block, toBlock=to_block
        )
        return _filter.get_all_entries()

    def processNewDDO(self, event):
        did, block, txid, contract_address, sender_address, flags, rawddo = self.get_event_data(event)
        debug_log(f'Process new DDO, did from event log:{did}')
        try:
            self._oceandb.read(did)
            logger.warning(f'{did} is already registered')
            return
        except Exception:
            pass

        logger.info(f'Start processing {EVENT_METADATA_CREATED} event: did={did}')
        debug_log(f'block {block}, contract: {contract_address}, Sender: {sender_address} , txid: {txid}')

        logger.debug(f'decoding with did {did} and flags {flags}')
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning(f'Could not decode ddo using flags {flags}')
            return

        msg, status = validate_data(data, f'event {EVENT_METADATA_CREATED}')
        if msg:
            logger.warning(msg)
            return

        _record = init_new_ddo(data)
        # this will be used when updating the doo
        _record['event'] = dict()
        _record['event']['txid'] = txid
        _record['event']['blockNo'] = block
        _record['event']['from'] = sender_address
        _record['event']['contract'] = contract_address

        if not is_valid_dict_remote(get_metadata_from_services(_record['service'])['attributes']):
            errors = list_errors(
                list_errors_dict_remote,
                get_metadata_from_services(_record['service'])['attributes'])
            logger.error(errors)
            return False

        try:
            self._oceandb.write(_record, did)
            name = _record["service"][0]["attributes"]["main"]["name"]
            debug_log(f'DDO saved: did={did}, name={name}, publisher={sender_address}')
            logger.info(f'Done processing {EVENT_METADATA_CREATED} event: did={did}. DDO SAVED TO DB')
            return True
        except (KeyError, Exception) as err:
            logger.error(f'encountered an error while saving the asset data to OceanDB: {str(err)}')
            return False

    def processUpdateDDO(self, event):
        did, block, txid, contract_address, sender_address, flags, rawddo = self.get_event_data(event)
        debug_log(f'Process update DDO, did from event log:{did}')
        try:
            asset = self._oceandb.read(did)
        except Exception as e:
            logger.warning(f'{did} is not registered, cannot update')
            return

        debug_log(f'block {block}, contract: {contract_address}, Sender: {sender_address} , txid: {txid}')

        # do not update if we have the same txid
        ddo_txid = asset['event']['txid']
        if txid == ddo_txid:
            logger.warning(f'asset has the same txid, no need to update: event-txid={txid} <> asset-event-txid={asset["event"]["txid"]}')
            return

        # check block
        ddo_block = asset['event']['blockNo']
        if int(block) <= int(ddo_block):
            logger.warning(
                f'asset was updated later (block: {ddo_block}) vs transaction block: {block}')
            return

        # check owner
        if not compare_eth_addresses(asset['publicKey'][0]['owner'], sender_address, logger):
            logger.warning(f'Transaction sender must mach ddo owner')
            return

        debug_log(f'decoding with did {did} and flags {flags}')
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning('Cound not decode ddo')
            return

        msg, status = validate_data(data, 'event update')
        if msg:
            logger.error(msg)
            return

        _record = init_new_ddo(data)
        _record['updated'] = get_timestamp()

        _record['event'] = dict()
        _record['event']['txid'] = txid
        _record['event']['blockNo'] = block
        _record['event']['from'] = sender_address
        _record['event']['contract'] = contract_address

        if not is_valid_dict_remote(get_metadata_from_services(_record['service'])['attributes']):
            errors = list_errors(list_errors_dict_remote, get_metadata_from_services(
                _record['service'])['attributes'])
            logger.error(errors)
            return

        try:
            self._oceandb.update(_record, did)
            logger.info(f'updated DDO saved to db successfully (did={did}).')
            return True
        except (KeyError, Exception) as err:
            logger.error(
                f'encountered an error while updating the asset data to OceanDB: {str(err)}')
            return

    def get_event_data(self, event):
        tx_id = event.transactionHash.hex()
        return (
            f'did:op:{remove_0x_prefix(event.args.dataToken)}',
            event.blockNumber,
            tx_id,
            event.address,
            get_sender_from_txid(self._web3, tx_id),
            event.args.get('flags', None),
            event.args.get('data', None)
        )

    def decode_ddo(self, rawddo, flags):
        debug_log(f'flags: {flags}')
        # debug_log(f'Before unpack rawddo:{rawddo}')
        if len(flags) < 1:
            debug_log(f'Set check_flags to 0!')
            check_flags = 0
        else:
            check_flags = flags[0]

        # always start with MSB -> LSB
        debug_log(f'checkflags: {check_flags}')
        # bit 2:  check if ddo is ecies encrypted
        if check_flags & 2:
            try:
                rawddo = self.ecies_decrypt(rawddo)
                logger.debug(f'Decrypted to {rawddo}')
            except (KeyError, Exception) as err:
                logger.error(f'Failed to decrypt: {str(err)}')

        # bit 1:  check if ddo is lzma compressed
        if check_flags & 1:
            try:
                rawddo = Lzma.decompress(rawddo)
                logger.debug(f'Decompressed to {rawddo}')
            except (KeyError, Exception) as err:
                logger.error(f'Failed to decompress: {str(err)}')

        logger.debug(f'After unpack rawddo:{rawddo}')
        try:
            ddo = json.loads(rawddo)
            return ddo
        except (KeyError, Exception) as err:
            logger.error(f'encountered an error while decoding the ddo: {str(err)}')
            return None

    def ecies_decrypt(self, rawddo):
        if self._ecies_account is not None:
            key = eth_keys.KeyAPI.PrivateKey(self._ecies_account.privateKey)
            rawddo = ecies.decrypt(key.to_hex(), rawddo)
        return rawddo
