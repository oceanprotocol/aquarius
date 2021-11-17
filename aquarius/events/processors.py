#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
from datetime import datetime
import hashlib
import json
import logging
import os
from abc import ABC
from hashlib import sha256

import requests
from jsonsempai import magic  # noqa: F401
from artifacts import ERC20Template

from aquarius.app.auth_util import compare_eth_addresses
from aquarius.ddo_checker.shacl_checker import validate_dict
from aquarius.events.decryptor import decrypt_ddo
from aquarius.graphql import get_number_orders

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
        return (
            sha256(json.dumps(asset).encode("utf-8")).hexdigest() == document_hash.hex()
        )

    def add_aqua_data(self, record):
        """Adds keys that are specific to Aquarius, on top of the DDO structure:
        event, nft, datatokens."""
        block_info = self._web3.eth.get_block(self.event.blockNumber)
        block_time = datetime.fromtimestamp(block_info["timestamp"]).isoformat()

        record["event"] = {
            "tx": self.txid,
            "block": self.block,
            "from": self.sender_address,
            "contract": self.event.address,
            "datetime": block_time,
        }

        record["nft"] = {
            "address": self.dt_contract.address,
            "name": self.dt_contract.caller.name(),
            "symbol": self.dt_contract.caller.symbol(),
            "state": self.dt_contract.caller.metaDataState(),
            "owner": self.dt_contract.caller.ownerOf(1),
        }

        record["datatokens"] = self.get_tokens_info()
        # TODO: record["stats"]["consumes"]

        # Initialise stats field
        record["stats"] = {}

        return record, block_time

    def get_tokens_info(self):
        datatokens = []
        tokens = self.dt_contract.caller.getTokensList()
        for token in tokens:
            token_contract = self._web3.eth.contract(
                abi=ERC20Template.abi, address=token
            )

            datatokens.append(
                {
                    "adddress": token,
                    "name": token_contract.caller.name(),
                    "symbol": token_contract.caller.symbol(),
                    "serviceId": "TODO",
                }
            )

        return datatokens


class MetadataCreatedProcessor(EventProcessor):
    def is_publisher_allowed(self, publisher_address):
        logger.debug(f"checking allowed publishers: {publisher_address}")
        if not self.allowed_publishers:
            return True

        publisher_address = self._web3.toChecksumAddress(publisher_address)
        return publisher_address in self.allowed_publishers

    def make_record(self, data):
        _record = copy.deepcopy(data)
        _record, block_time = self.add_aqua_data(_record)
        _record["nft"]["created"] = block_time

        # the event record will be used when updating the ddo
        version = _record.get("version")
        if not version:
            logger.error("DDO has no version.")
            return False

        valid_remote, errors = validate_dict(_record)

        if not valid_remote:
            logger.error(
                f"New ddo has validation errors: {errors} \nfor record:\n {_record}"
            )
            return False

        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["stats"]["isInPurgatory"] = "true"
        else:
            _record["stats"]["isInPurgatory"] = "false"

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
            f"Process new DDO, did from event log: {did}, block {self.block}, "
            f"contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
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

        _record = self.make_record(asset)
        if _record:
            try:
                record_str = json.dumps(_record)
                self._es_instance.write(record_str, did)
                _record = json.loads(record_str)
                name = _record["metadata"]["name"]
                created = _record["created"]
                logger.info(
                    f"DDO saved: did={did}, name={name}, "
                    f"publisher={sender_address}, created={created}, chainId={self._chain_id}"
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
        _record = copy.deepcopy(data)
        _record, _ = self.add_aqua_data(_record)
        _record["nft"]["created"] = old_asset["nft"]["created"]

        version = _record.get("version")
        if not version:
            logger.error("DDO has no version.")
            return False

        valid_remote, errors = validate_dict(_record)

        if not valid_remote:
            logger.error(f"ddo update has validation errors: {errors}")
            return False

        # check purgatory only if asset is valid
        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["stats"]["isInPurgatory"] = "true"
        else:
            _record["stats"]["isInPurgatory"] = old_asset.get("stats", "false").get(
                "isInPurgatory", "false"
            )

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
            f"Process new DDO, did from event log:{did}, block {self.block}, "
            f"contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
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
                self.dt_contract,
                self.sender_address,
                self._es_instance,
                self._web3,
                self.allowed_publishers,
                self.purgatory,
                self._chain_id,
            )

            return event_processor.process()

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
        ddo_txid = old_asset["event"]["tx"]
        if self.txid == ddo_txid:
            logger.warning(
                "old asset has the same txid, no need to update: "
                f'event-txid={self.txid} <> asset-event-txid={old_asset["event"]["tx"]}'
            )
            return False

        # check block
        ddo_block = old_asset["event"]["block"]
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

        return True


class OrderStartedProcessor:
    def __init__(self, token_address, es_instance, last_sync_block, chain_id):
        # TODO: this is not the correct did, see comment in events monitor. Putting this on hold for now
        self.did = "did:op:" + hashlib.sha256((token_address + str(chain_id)).encode("UTF-8")).hexdigest()
        self.es_instance = es_instance
        self.token_address = token_address
        self.last_sync_block = last_sync_block

        try:
            self.asset = self.es_instance.read(self.did)
        except Exception:
            self.asset = None

    def process(self):
        if not self.asset:
            return

        number_orders = get_number_orders(self.token_address, self.last_sync_block)
        self.asset["ordersCount"] = number_orders

        self.es_instance.update(self.asset, self.did)

        return self.asset
