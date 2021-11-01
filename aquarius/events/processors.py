#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from abc import ABC
from datetime import datetime
from hashlib import sha256

import requests
from eth_utils import add_0x_prefix
from jsonsempai import magic  # noqa: F401

from aquarius.app.auth_util import compare_eth_addresses
from aquarius.app.util import (
    DATETIME_FORMAT,
    format_timestamp,
    get_metadata_from_services,
    init_new_ddo,
    validate_data,
)
from aquarius.ddo_checker.ddo_checker import validate_dict
from aquarius.events.constants import EVENT_METADATA_CREATED
from aquarius.events.decryptor import decrypt_ddo

logger = logging.getLogger(__name__)


class EventProcessor(ABC):
    def __init__(
        self,
        event,
        dt_contract,
        sender_address,
        es_instance,
        web3,
        allowed_publishers,
        purgatory,
        chain_id,
    ):
        """Initialises common Event processing properties."""
        self.event = event
        self.dt_contract = dt_contract
        self.sender_address = sender_address
        self.block = event.blockNumber
        self.txid = self.event.transactionHash.hex()

        self._es_instance = es_instance
        self._web3 = web3
        self.allowed_publishers = allowed_publishers
        self.purgatory = purgatory
        self._chain_id = chain_id

    def check_permission(self, publisher_address):
        if not os.getenv("RBAC_SERVER_URL") or not publisher_address:
            return True

        event_type = (
            "publish"
            if self.__class__.__name__ == "MetadataCreatedProcessor"
            else "update"
        )
        address = publisher_address
        payload = {
            "eventType": event_type,
            "component": "metadatacache",
            "credentials": {"type": "address", "value": address},
        }

        try:
            return requests.post(os.getenv("RBAC_SERVER_URL"), json=payload).json()
        except Exception:
            return False

    def check_document_hash(self, asset):
        document_hash = self.event.args.metaDataHash
        return sha256(json.dumps(asset).encode("utf-8")).hexdigest() == document_hash.hex()


class MetadataCreatedProcessor(EventProcessor):
    def is_publisher_allowed(self, publisher_address):
        logger.debug(f"checking allowed publishers: {publisher_address}")
        if not self.allowed_publishers:
            return True

        publisher_address = self._web3.toChecksumAddress(publisher_address)
        return publisher_address in self.allowed_publishers

    def make_record(self, data):
        # to avoid unnecesary get_block calls, always init with timestamp 0 and get it from chain if the asset is valid
        _record = init_new_ddo(data, 0)

        # the event record will be used when updating the ddo
        _record["event"] = {
            "txid": self.txid,
            "blockNo": self.block,
            "from": self.event.address,
            "contract": self.event.address,
            "update": False,
        }

        version = _record.get('version', 'v3')
        content_to_validate = get_metadata_from_services(_record["service"]) if version == 'v3' else _record
        valid_remote, errors = validate_dict(content_to_validate)

        if not valid_remote:
            logger.error(
                f"New ddo has validation errors: {errors} \nfor record:\n {_record}"
            )
            return False

        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["isInPurgatory"] = "true"
        else:
            _record["isInPurgatory"] = "false"

        # add info related to blockchain
        blockInfo = self._web3.eth.get_block(self.event.blockNumber)
        _record["created"] = format_timestamp(
            datetime.fromtimestamp(blockInfo["timestamp"]).strftime(DATETIME_FORMAT)
        )
        _record["updated"] = _record["created"]
        _record["chainId"] = self._chain_id

        dt_address = _record.get("dataToken")
        assert dt_address == add_0x_prefix(self.did[len("did:op:") :])
        if dt_address:
            _record["dataTokenInfo"] = {
                "address": self.dt_contract.address,
                "name": self.dt_contract.caller.name(),
                "symbol": self.dt_contract.caller.symbol(),
            }

        return _record

    def process(self):
        txid = self.txid
        asset = decrypt_ddo(
            self._web3,
            self.event.args.decryptorUrl,
            self.event.address,
            self._chain_id,
            txid,
        )

        if not self.check_document_hash(asset):
            return False

        self.did = asset["id"]
        did, sender_address = self.did, self.sender_address
        logger.info(
            f"Process new DDO, did from event log:{did}, block {self.block}, contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
        )

        if not self.is_publisher_allowed(sender_address):
            logger.warning(f"Sender {sender_address} is not in ALLOWED_PUBLISHERS.")
            return

        try:
            ddo = self._es_instance.read(did)
            if ddo["chainId"] == self._chain_id:
                logger.warning(f"{did} is already registered on this chainId")
                return
        except Exception:
            pass

        permission = self.check_permission(sender_address)
        if not permission:
            raise Exception("RBAC permission denied.")

        msg, _ = validate_data(asset, f"event {EVENT_METADATA_CREATED}")
        if msg:
            logger.warning(msg)
            return

        _record = self.make_record(asset)
        if _record:
            try:
                record_str = json.dumps(_record)
                self._es_instance.write(record_str, did)
                _record = json.loads(record_str)
                name = _record["service"][0]["attributes"]["main"]["name"]
                created = _record["created"]
                logger.info(
                    f"DDO saved: did={did}, name={name}, publisher={sender_address}, created={created}, chainId={self._chain_id}"
                )
                return True
            except (KeyError, Exception) as err:
                logger.error(
                    f"encountered an error while saving the asset data to ES: {str(err)}"
                )
        return False


class MetadataUpdatedProcessor(EventProcessor):
    def make_record(self, data, old_asset):
        # to avoid unnecesary get_block calls, always init with timestamp 0 and get it from chain if the asset is valid
        _record = init_new_ddo(data, 0)
        # make sure that we do not alter created flag
        _record["created"] = old_asset["created"]

        _record["event"] = {
            "txid": self.txid,
            "blockNo": self.block,
            "from": self.event.address,
            "contract": self.event.address,
            "update": True,
        }

        version = _record.get('version', 'v3')
        content_to_validate = get_metadata_from_services(_record["service"]) if version == 'v3' else _record
        valid_remote, errors = validate_dict(content_to_validate)

        if not valid_remote:
            logger.error(f"ddo update has validation errors: {errors}")
            return False

        # check purgatory only if asset is valid
        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["isInPurgatory"] = "true"
        else:
            _record["isInPurgatory"] = old_asset.get("isInPurgatory", "false")

        # add info related to blockchain
        blockInfo = self._web3.eth.get_block(self.event.blockNumber)
        _record["updated"] = format_timestamp(
            datetime.fromtimestamp(blockInfo["timestamp"]).strftime(DATETIME_FORMAT)
        )
        _record["chainId"] = self._chain_id
        dt_address = _record.get("dataToken")
        assert dt_address == add_0x_prefix(self.did[len("did:op:") :])
        if dt_address:
            _record["dataTokenInfo"] = {
                "address": self.dt_contract.address,
                "name": self.dt_contract.caller.name(),
                "symbol": self.dt_contract.caller.symbol(),
            }

        return _record

    def process(self):
        txid = self.txid
        asset = decrypt_ddo(
            self._web3,
            self.event.args.decryptorUrl,
            self.event.address,
            self._chain_id,
            txid,
        )

        if not self.check_document_hash(asset):
            return False

        self.did = asset["id"]
        did, sender_address = self.did, self.sender_address
        logger.info(
            f"Process new DDO, did from event log:{did}, block {self.block}, contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
        )

        permission = self.check_permission(sender_address)
        if not permission:
            raise Exception("RBAC permission denied.")

        try:
            old_asset = self._es_instance.read(did)
        except Exception:
            # check if this asset was deleted/hidden due to some violation issues
            # if so, don't add it again
            logger.warning(f"{did} is not registered, will add it as a new DDO.")
            event_processor = MetadataCreatedProcessor(
                self.event,
                self.contract,
                self.sender_address,
                self._es_instance,
                self._web3,
                self.allowed_publishers,
                self.purgatory,
                self._chain_id,
            )
            event_processor.process()
            return False

        is_updateable = self.check_update(asset, old_asset, sender_address)
        if not is_updateable:
            return False

        _record = self.make_record(asset, old_asset)
        if _record:
            try:
                self._es_instance.update(json.dumps(_record), did)
                updated = _record["updated"]
                logger.info(f"updated DDO did={did}, updated: {updated}")
                return True
            except (KeyError, Exception) as err:
                logger.error(
                    f"encountered an error while updating the asset data to ES: {str(err)}"
                )

        return False

    def check_update(self, new_asset, old_asset, sender_address):
        # do not update if we have the same txid
        ddo_txid = old_asset["event"]["txid"]
        if self.txid == ddo_txid:
            logger.warning(
                f'old asset has the same txid, no need to update: event-txid={self.txid} <> asset-event-txid={asset["event"]["txid"]}'
            )
            return False

        # check block
        ddo_block = old_asset["event"]["blockNo"]
        if int(self.block) <= int(ddo_block):
            logger.warning(
                f"asset was updated later (block: {ddo_block}) vs transaction block: {self.block}"
            )
            return False

        if not compare_eth_addresses(
            old_asset["publicKey"][0]["owner"], sender_address, logger
        ):
            logger.warning("Transaction sender must mach ddo owner")
            return False

        msg, _ = validate_data(new_asset, "event update")
        if msg:
            logger.error(msg)
            return False

        return True
