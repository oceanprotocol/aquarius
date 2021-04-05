#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from abc import ABC
from eth_utils import add_0x_prefix, remove_0x_prefix
import json
import logging

from plecos.plecos import is_valid_dict_remote, list_errors_dict_remote
from aquarius.app.util import (
    init_new_ddo,
    validate_data,
    get_metadata_from_services,
    list_errors,
)
from aquarius.events.constants import EVENT_METADATA_CREATED
from aquarius.events.util import get_datatoken_info
from aquarius.events.decryptor import Decryptor

logger = logging.getLogger(__name__)
debug_log = logger.debug


class EventProcessor(ABC):
    def __init__(self, event, oceandb, web3, ecies_account):
        self.event = event
        self.did = f"did:op:{remove_0x_prefix(self.event.args.dataToken)}"
        self.block = event.blockNumber
        self.txid = self.event.transactionHash.hex()
        self.contract_address = self.event.address
        self.sender_address = self.event.args.get(
            "createdBy", self.event.args.get("updatedBy")
        )
        self.flags = event.args.get("flags", None)
        self.rawddo = event.args.get("data", None)

        self._oceandb = oceandb
        self._web3 = web3
        self.decryptor = Decryptor(ecies_account)

        blockInfo = self._web3.eth.getBlock(self.event.blockNumber)
        self.timestamp = blockInfo["timestamp"]


class MetadataCreatedProcessor(EventProcessor):
    def setAllowedPublishers(self, allowed_publishers):
        self.allowed_publishers = allowed_publishers

    def is_publisher_allowed(self, publisher_address):
        logger.debug(f"checking allowed publishers: {publisher_address}")
        if not self.allowed_publishers:
            return True

        publisher_address = self._web3.toChecksumAddress(publisher_address)
        return publisher_address in self.allowed_publishers

    def make_record(self, data):
        _record = init_new_ddo(data, self.timestamp)
        # this will be used when updating the doo
        _record["event"] = {
            "txid": self.txid,
            "blockNo": self.block,
            "from": self.sender_address,
            "contract": self.contract_address,
        }

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
        assert dt_address == add_0x_prefix(self.did[len("did:op:") :])
        if dt_address:
            _record["dataTokenInfo"] = get_datatoken_info(dt_address)

        if not is_valid_dict_remote(get_metadata_from_services(_record["service"])):
            errors = list_errors(
                list_errors_dict_remote, get_metadata_from_services(_record["service"])
            )
            logger.error(f"New ddo has validation errors: {errors}")
            return False

        _record["isInPurgatory"] = "false"

        return _record

    def process(self):
        did, sender_address = self.did, self.sender_address
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
            f"block {self.block}, contract: {self.contract_address}, Sender: {sender_address} , txid: {self.txid}"
        )

        logger.debug(f"decoding with did {did} and flags {self.flags}")
        data = self.decryptor.decode_ddo(self.rawddo, self.flags)
        if data is None:
            logger.warning(f"Could not decode ddo using flags {self.flags}")
            return

        msg, _ = validate_data(data, f"event {EVENT_METADATA_CREATED}")
        if msg:
            logger.warning(msg)
            return

        _record = self.make_record(data)

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
