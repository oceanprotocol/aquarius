#  Copyright 2020 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import time
import copy
from web3 import Web3
import lzma as Lzma
import ecies
import eth_keys
import json
from datetime import datetime
from threading import Thread
from oceandb_driver_interface import OceanDb
from aquarius.app.util import (
    reorder_services_list,
    make_paginate_response,
    datetime_converter,
    validate_date_format,
    format_timestamp,
    get_timestamp,
    get_main_metadata,
    get_metadata_from_services,
    check_no_urls_in_files,
    check_required_attributes,
    sanitize_record,
    list_errors,
    validate_data,
    get_sender_from_txid
)
from aquarius.app.auth_util import compare_eth_addresses, can_update_did, can_update_did_from_allowed_updaters
from plecos.plecos import (
    is_valid_dict_local,
    is_valid_dict_remote,
    list_errors_dict_local,
    list_errors_dict_remote,
)

logger = logging.getLogger(__name__)


debug_log = logger.debug


class Events:
    _instance = None

    def __init__(self, rpc, contract_address, config_file):
        self._oceandb = OceanDb(config_file).plugin
        self._rpc = rpc
        self._web3 = Web3(Web3.HTTPProvider(rpc))
        self._contract_address = contract_address
        self._ecies_private_key = os.getenv('EVENTS_ECIES_PRIVATE_KEY', None)
        self._monitor_is_on = False
        try:
            self._monitor_sleep_time = os.getenv(
                'OCN_EVENTS_MONITOR_QUITE_TIME', 3)
        except ValueError:
            self._monitor_sleep_time = 3
        self._monitor_sleep_time = max(self._monitor_sleep_time, 3)
        if not self._web3.isAddress(contract_address):
            logger.error(
                f"Contract address {contract_address} is not a valid address. Events thread not starting")
            self._contract = None
            return
        path = './aquarius/artifacts/DDO.json'
        data = json.load(open(path))
        self._contract = self._web3.eth.contract(
            address=contract_address, abi=data['abi'])

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
        logger.error(
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
                try:
                    last_block = self.get_last_processed_block()

                except Exception as e:
                    logger.info(e)
                    last_block = 0

                current_block = self._web3.eth.blockNumber
                logger.debug(
                    f'Last block:{last_block}, Current:{current_block}')

                events_filter = self._contract.events.DDOOwnershipTransferred.createFilter(
                    fromBlock=last_block)
                for event in events_filter.get_all_entries():
                    self.processNewDDO(event)

                events_filter = self._contract.events.DDOCreated.createFilter(
                    fromBlock=last_block)
                for event in events_filter.get_all_entries():
                    self.processTransferOwnership(event)

                events_filter = self._contract.events.DDOUpdated.createFilter(
                    fromBlock=last_block)
                for event in events_filter.get_all_entries():
                    self.processUpdateDDO(event)

                self.store_last_processed_block(current_block+1)

            except (KeyError, Exception) as e:
                logger.error(f'Error processing event: {e}')

            time.sleep(self._monitor_sleep_time)

    def get_last_processed_block(self):
        last_block_record = self._oceandb.read('events_last_block')
        last_block = last_block_record['last_block']
        return (last_block)

    def store_last_processed_block(self, block):
        record = {"last_block": block}
        self._oceandb.update(record, 'events_last_block')

    def processNewDDO(self, event):
        logger.debug(f'Event:{event}')
        block = event['blockNumber']
        contract_address = event['address']
        txid = event['transactionHash'].hex()
        address = get_sender_from_txid(self._web3, txid)
        logger.debug(
            f'block {block}, contract: {contract_address}, Sender: {address} , txid: {txid}')
        flags = event['args']['flags']
        rawddo = event['args']['data']
        logger.error(f'decoding with flags {flags}')
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning('Cound not decode ddo')
            return
        did = data['id']
        msg, status = validate_data(data, 'event register')
        if msg:
            logger.warning(msg)
            return
        try:
            asset = self._oceandb.read(did)
            logger.warning(f'{did} is already registred')
            return
        except Exception as e:
            asset = None
        _record = dict()
        _record = copy.deepcopy(data)
        _record['created'] = format_timestamp(data['created'])
        _record['updated'] = _record['created']
        # this will be used when updating the doo
        _record['event'] = dict()
        _record['event']['txid'] = txid
        _record['event']['blockNo'] = block
        _record['event']['from'] = address
        _record['event']['contract'] = contract_address
        if 'accesssWhiteList' not in data:
            _record['accesssWhiteList'] = []
        else:
            if not isinstance(data['accesssWhiteList'], list):
                _record['accesssWhiteList'] = []
            else:
                _record['accesssWhiteList'] = data['accesssWhiteList']
        for service in _record['service']:
            service['attributes']['main']['dateCreated'] = format_timestamp(
                data['created'])
            service['attributes']['main']['datePublished'] = get_timestamp()
        _record['service'] = reorder_services_list(_record['service'])
        if not is_valid_dict_remote(get_metadata_from_services(_record['service'])['attributes']):
            errors = list_errors(list_errors_dict_remote, get_metadata_from_services(
                _record['service'])['attributes'])
            logger.error(errors)
            return
        try:
            self._oceandb.write(_record, did)
            return
        except (KeyError, Exception) as err:
            logger.error(
                f'encounterd an error while saving the asset data to OceanDB: {str(err)}')
            return
        logger.debug(f'ddo saved')
        return True

    def processUpdateDDO(self, event):
        logger.info(f'Event:{event}')
        block = event['blockNumber']
        txid = event['transactionHash'].hex()
        contract_address = event['address']
        address = get_sender_from_txid(self._web3, txid)
        logger.debug(
            f'block {block}, contract: {contract_address}, Sender: {address} , txid: {txid}')
        flags = event['args']['flags']
        rawddo = event['args']['data']
        logger.error(f'decoding with flags {flags}')
        data = self.decode_ddo(rawddo, flags)
        if data is None:
            logger.warning('Cound not decode ddo')
            return
        did = data['id']
        msg, status = validate_data(data, 'event update')
        if msg:
            logger.error(msg)
            return
        try:
            asset = self._oceandb.read(did)
        except Exception as e:
            logger.warning(f'{did} is not registred, cannot update')
            return
        # check owner
        if not compare_eth_addresses(asset['publicKey'][0]['owner'], address, logger):
            logger.warning(f'Transaction sender must mach ddo owner')
            return
        # check block
        ddo_block = asset['event']['blockNo']
        if int(block) <= int(ddo_block):
            logger.warning(
                f'asset was updated later (block: {ddo_block}) vs transaction block: {block}')
            return
        # do not update if we have the same txid
        ddo_txid = asset['event']['txid']
        if txid == ddo_txid:
            logger.warning(f'asset has the same txid, no need to update')
            return
        _record = dict()
        _record = copy.deepcopy(data)
        _record['created'] = format_timestamp(data['created'])
        _record['updated'] = _record['created']
        # this will be used when updating the doo
        _record['event'] = dict()
        _record['event']['txid'] = txid
        _record['event']['blockNo'] = block
        _record['event']['from'] = address
        _record['event']['contract'] = contract_address
        if 'accesssWhiteList' not in data:
            _record['accesssWhiteList'] = []
        else:
            if not isinstance(data['accesssWhiteList'], list):
                _record['accesssWhiteList'] = []
            else:
                _record['accesssWhiteList'] = data['accesssWhiteList']
        for service in _record['service']:
            service['attributes']['main']['dateCreated'] = format_timestamp(
                data['created'])
            service['attributes']['main']['datePublished'] = get_timestamp()
        _record['service'] = reorder_services_list(_record['service'])
        if not is_valid_dict_remote(get_metadata_from_services(_record['service'])['attributes']):
            errors = list_errors(list_errors_dict_remote, get_metadata_from_services(
                _record['service'])['attributes'])
            logger.error(errors)
            return
        try:
            self._oceandb.update(_record, did)
            return
        except (KeyError, Exception) as err:
            logger.error(
                f'encounterd an error while updating the asset data to OceanDB: {str(err)}')
            return
        return True

    def processTransferOwnership(self, event):
        logger.info(f'Event:{event}')
        block = event['blockNumber']
        txid = event['transactionHash'].hex()
        contract_address = event['address']
        address = get_sender_from_txid(self._web3, txid)
        logger.debug(
            f'block {block}, contract: {contract_address}, Sender: {address} , txid: {txid}')
        did = event['args']['did']
        try:
            asset = self._oceandb.read(did)
        except Exception as e:
            logger.warning(f'{did} is not registred, cannot update')
            return
        # check owner
        if not compare_eth_addresses(asset['publicKey'][0]['owner'], address, logger):
            logger.warning(f'Transaction sender must mach ddo owner')
            return
        # check block
        ddo_block = asset['event']['blockNo']
        if int(block) <= int(ddo_block):
            logger.warning(f'asset was updated later (block: {ddo_block}) vs transaction block: {block}')
            return
        # do not update if we have the same txid
        ddo_txid = asset['event']['txid']
        if txid == ddo_txid:
            logger.warning(f'asset has the same txid, no need to update')
            return
        _record = dict()
        _record = copy.deepcopy(data)
        # this will be used when updating the doo
        _record['event'] = dict()
        _record['event']['txid'] = txid
        _record['event']['blockNo'] = block
        _record['event']['from'] = address
        _record['event']['contract'] = contract_address
        _record['publicKey'][0]['owner'] = event['args']['owner']
       try:
            self._oceandb.update(_record, did)
            return
        except (KeyError, Exception) as err:
            logger.error(
                f'encounterd an error while updating the asset data to OceanDB: {str(err)}')
            return
        return True

    def decode_ddo(self, rawddo, flags):
        logger.debug(f'flags: {flags}')
        logger.debug(f'Before unpack rawddo:{rawddo}')
        if len(flags) < 1:
            logger.debug(f'Set check_flags to 0!')
            check_flags = 0
        else:
            check_flags = flags[0]
        # always start with MSB -> LSB
        logger.debug(f'checkflags: {check_flags}')
        # bit 2:  check if ddo is ecies encrypted
        if (check_flags & 2):
            try:
                rawddo = self.ecies_decrypt(rawddo)
                logger.debug(f'Decrypted to {rawddo}')
            except (KeyError, Exception) as err:
                logger.error(f'Failed to decrypt: {str(err)}')
        # bit 1:  check if ddo is lzma compressed
        if (check_flags & 1):
            try:
                rawddo = Lzma.decompress(rawddo)
                logger.debug(f'Decompressed to {rawddo}')
            except (KeyError, Exception) as err:
                logger.error(f'Failed to decompress: {str(err)}')
        logger.error(f'After unpack rawddo:{rawddo}')
        try:
            ddo = json.loads(rawddo)
            return(ddo)
        except (KeyError, Exception) as err:
            logger.error(
                f'encounterd an error while decoding the ddo: {str(err)}')
            return None


    def ecies_decrypt(self, rawddo):
        if self._ecies_private_key is not None:
            key = eth_keys.KeyAPI.PrivateKey(bytearray.fromhex(self._ecies_private_key[2:]))
            rawddo = ecies.decrypt(key.to_hex(), rawddo)
        return(rawddo)
