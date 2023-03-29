#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
import logging
import os
from abc import ABC
from datetime import datetime
from eth_utils.address import to_checksum_address

from aquarius.ddo_checker.shacl_checker import validate_dict
from aquarius.events.constants import (
    AquariusCustomDDOFields,
    EventTypes,
    MetadataStates,
)
from aquarius.events.decryptor import decrypt_ddo
from aquarius.events.proof_checker import check_metadata_proofs
from aquarius.events.util import (
    make_did,
    get_dt_factory,
    update_did_state,
    get_erc20_contract,
    get_nft_contract,
)
from aquarius.graphql import get_number_orders_price
from aquarius.rbac import RBAC
from web3.logs import DISCARD

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
        self.metadata_proofs = None

    def check_permission(self, publisher_address):
        if not os.getenv("RBAC_SERVER_URL") or not publisher_address:
            return True

        event_type = (
            "publish"
            if self.__class__.__name__ == "MetadataCreatedProcessor"
            else "update"
        )

        return RBAC.check_permission_rbac(event_type, publisher_address)

    def add_aqua_data(self, record):
        """Adds keys that are specific to Aquarius, on top of the DDO structure:
        event, nft, datatokens."""
        block_info = self._web3.eth.get_block(self.event.blockNumber)
        block_time = datetime.fromtimestamp(block_info["timestamp"]).isoformat()

        record[AquariusCustomDDOFields.EVENT] = {
            "tx": self.txid,
            "block": self.block,
            "from": self.sender_address,
            "contract": self.event.address,
            "datetime": block_time,
        }

        record[AquariusCustomDDOFields.NFT] = {
            "address": self.dt_contract.address,
            "name": self._get_contract_attribute(self.dt_contract, "name"),
            "symbol": self._get_contract_attribute(self.dt_contract, "symbol"),
            "state": self._get_contract_attribute(self.dt_contract, "metaDataState"),
            "tokenURI": self._get_contract_attribute(self.dt_contract, "tokenURI", [1]),
            "owner": self.get_nft_owner(),
        }

        record[AquariusCustomDDOFields.DATATOKENS] = self.get_tokens_info(record)

        order_count, price = get_number_orders_price(
            self.dt_contract.address, self.block, self._chain_id
        )
        record[AquariusCustomDDOFields.STATS] = {
            "allocated": 0,
            "orders": order_count,
            "price": price,
        }

        return record, block_time

    def soft_delete_ddo(self, did: str):
        """Deletes all fields from ES for a given DDO except for the fields listed in AquariusCustomDDOFields"""
        old_asset = self._es_instance.read(did)
        soft_deleted_asset = {
            k: copy.deepcopy(old_asset)[k]
            for k in [
                custom_field
                for custom_field in AquariusCustomDDOFields.get_all_values()
            ]
        }
        return self._es_instance.update(soft_deleted_asset, did)

    def update_aqua_nft_state_data(self, new_state: str, did: str):
        """Updates NFT state field from the aquarius custom fields data listed in AquariusCustomDDOFields for a given
        DID"""
        asset_to_update = self._es_instance.read(did)
        asset_to_update[AquariusCustomDDOFields.NFT]["state"] = new_state

        return self._es_instance.update(asset_to_update, did)

    def get_tokens_info(self, record):
        datatokens = []
        for service in record.get("services", []):
            token_contract = get_erc20_contract(self._web3, service["datatokenAddress"])

            datatokens.append(
                {
                    "address": service["datatokenAddress"],
                    "name": self._get_contract_attribute(token_contract, "name"),
                    "symbol": self._get_contract_attribute(token_contract, "symbol"),
                    "serviceId": service["id"],
                }
            )

        return datatokens

    def _get_contract_attribute(self, contract, attr_name, args=None):
        data = ""
        args = args if args else []
        try:
            data = getattr(contract.caller, attr_name)(*args)
        except Exception as e:
            logger.warn(f"Cannot get token {attr_name}: {e}")
            pass
        return data

    def get_nft_owner(self):
        data = ""
        try:
            data = self.dt_contract.caller.ownerOf(1)
        except Exception as e:
            logger.warn(f"Cannot get NFT ownerOf: {e}")
            pass
        return data


class MetadataCreatedProcessor(EventProcessor):
    def is_publisher_allowed(self, publisher_address):
        logger.debug(f"checking allowed publishers: {publisher_address}")
        if not self.allowed_publishers:
            return True

        publisher_address = to_checksum_address(publisher_address)
        return publisher_address in self.allowed_publishers

    def make_record(self, data):
        _record = copy.deepcopy(data)
        _record, block_time = self.add_aqua_data(_record)
        _record["nft"]["created"] = block_time

        # the event record will be used when updating the ddo
        version = _record.get("version")
        if not version:
            msg = "DDO has no version."
            logger.error(msg)
            return False, msg

        valid_remote, errors = validate_dict(
            _record, self._chain_id, self.dt_contract.address
        )

        if not valid_remote:
            msg = f"New ddo has validation errors: {errors} \nfor record:\n {_record}"
            logger.error(msg)
            return False, msg

        _record["purgatory"] = {}
        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["purgatory"]["state"] = True
        else:
            _record["purgatory"]["state"] = False

        return _record, None

    def restore_nft_state(self, ddo, state):
        ddo["nft"]["state"] = state
        record_str = json.dumps(ddo)
        self._es_instance.update(record_str, self.did)
        _record = json.loads(record_str)
        name = _record["metadata"]["name"]
        sender_address = _record["nft"]["owner"]
        logger.info(
            f"DDO saved: did={self.did}, name={name}, "
            f"publisher={sender_address}, chainId={self._chain_id}, updated state={state}"
        )

    def process(self):
        txid = self.txid
        expected_did = make_did(self.event.address, self._chain_id)
        logger.info(
            f"Process new DDO: {expected_did}, block {self.block}, "
            f"contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
        )
        dt_factory = get_dt_factory(self._web3, self._chain_id)
        if dt_factory.caller.erc721List(
            to_checksum_address(self.event.address)
        ) != to_checksum_address(self.event.address):
            error = "nft not deployed by our factory"
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            logger.error(error)

            return

        if not check_metadata_proofs(self._web3, self.metadata_proofs):
            error = "Failed to validate metadata_proofs"
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            logger.error(error)
            return

        # if not authorized, will return False, which is a graceful failure
        # otherwise it will raise an exception
        asset = decrypt_ddo(
            self._web3,
            self.event.args.decryptorUrl,
            self.event.address,
            self._chain_id,
            txid,
            self.event.args.metaDataHash,
            self._es_instance,
        )
        if not asset:
            logger.info("Decrypt ddo failed.Failing gracefully.")
            return

        self.did = asset["id"]
        did, sender_address = self.did, self.sender_address

        if not self.is_publisher_allowed(sender_address):
            error = f"Sender {sender_address} is not in ALLOWED_PUBLISHERS."
            logger.warning(error)
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            return

        try:
            ddo = self._es_instance.read(did)
            if ddo["chainId"] == self._chain_id:
                update_did_state(
                    self._es_instance,
                    self.event.address,
                    self._chain_id,
                    txid,
                    True,
                    None,
                )
                if ddo["nft"]["state"] == MetadataStates.ACTIVE:
                    logger.warning(f"{did} is already registered on this chainId")
                    return
                self.restore_nft_state(ddo, asset["nft"]["state"])
                return True
        except Exception:
            pass

        permission = self.check_permission(sender_address)
        if not permission:
            error = "RBAC permission denied."
            logger.info(error)
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            return

        _record, error_msg = self.make_record(asset)

        if _record:
            try:
                record_str = json.dumps(_record)
                self._es_instance.update(record_str, did)
                _record = json.loads(record_str)
                name = _record["metadata"]["name"]
                logger.info(
                    f"DDO saved: did={did}, name={name}, "
                    f"publisher={sender_address}, chainId={self._chain_id}"
                )
                update_did_state(
                    self._es_instance,
                    self.event.address,
                    self._chain_id,
                    txid,
                    True,
                    None,
                )
                return True
            except (KeyError, Exception) as err:
                error = f"encountered an error while saving the asset data to ES: {str(err)}"
                logger.error(error)
                update_did_state(
                    self._es_instance,
                    self.event.address,
                    self._chain_id,
                    txid,
                    False,
                    error,
                )
        else:
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error_msg,
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
            msg = "DDO has no version."
            logger.error()
            return False, msg

        valid_remote, errors = validate_dict(
            _record, self._chain_id, self.dt_contract.address
        )
        if not valid_remote:
            msg = (
                f"Updated ddo has validation errors: {errors} \nfor record:\n {_record}"
            )
            logger.error(msg)
            return False, msg

        # check purgatory only if asset is valid
        old_purgatory = old_asset.get("purgatory", {})
        _record["purgatory"] = old_purgatory

        if self.purgatory and self.purgatory.is_account_banned(self.sender_address):
            _record["purgatory"]["state"] = True
        else:
            _record["purgatory"]["state"] = old_purgatory.get("state", False)

        return _record, None

    def process(self):
        txid = self.txid
        expected_did = make_did(self.event.address, self._chain_id)
        logger.info(
            f"Process DDO update: {expected_did}, block {self.block}, "
            f"contract: {self.event.address}, txid: {self.txid}, chainId: {self._chain_id}"
        )
        dt_factory = get_dt_factory(self._web3, self._chain_id)
        if dt_factory.caller.erc721List(
            to_checksum_address(self.event.address)
        ) != to_checksum_address(self.event.address):
            error = "nft not deployed by our factory"
            logger.error(error)
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            return

        if not check_metadata_proofs(self._web3, self.metadata_proofs):
            error = "Failed to validate metadata_proofs"
            logger.error(error)
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            return

        # if not authorized, will return False, which is a graceful failure
        # otherwise it will raise an exception
        asset = decrypt_ddo(
            self._web3,
            self.event.args.decryptorUrl,
            self.event.address,
            self._chain_id,
            txid,
            self.event.args.metaDataHash,
            self._es_instance,
        )
        if not asset:
            logger.info("Decrypt ddo failed.Failing gracefully.")
            return

        self.did = asset["id"]
        did, sender_address = self.did, self.sender_address

        permission = self.check_permission(sender_address)
        if not permission:
            error = "RBAC permission denied."
            logger.info(error)
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error,
            )
            return

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

        _record, error_msg = self.make_record(asset, old_asset)
        if _record:
            try:
                self._es_instance.update(json.dumps(_record), did)
                logger.info(f"updated DDO did={did}")
                update_did_state(
                    self._es_instance,
                    self.event.address,
                    self._chain_id,
                    txid,
                    True,
                    None,
                )
                return True
            except (KeyError, Exception) as err:
                error = f"encountered an error while updating the asset data to ES: {str(err)}"
                logger.error(error)
                update_did_state(
                    self._es_instance,
                    self.event.address,
                    self._chain_id,
                    txid,
                    False,
                    error,
                )
        else:
            update_did_state(
                self._es_instance,
                self.event.address,
                self._chain_id,
                txid,
                False,
                error_msg,
            )
            return False

    def check_update(self, new_asset, old_asset, sender_address):
        # do not update if we have the same txid
        ddo_txid = old_asset["event"]["tx"]
        if self.txid == ddo_txid:
            logger.warning(
                "old asset has the same txid, no need to update: "
                + f"event-txid={self.txid} <> asset-event-txid={ddo_txid}"
            )
            return False

        # check block
        ddo_block = old_asset["event"]["block"]
        if int(self.block) <= int(ddo_block):
            logger.warning(
                f"asset was updated later (block: {ddo_block}) vs transaction block: {self.block}"
            )
            return False

        return True


class OrderStartedProcessor:
    def __init__(self, token_address, es_instance, last_sync_block, chain_id):
        self.did = make_did(token_address, chain_id)
        self.chain_id = chain_id
        self.es_instance = es_instance
        self.token_address = token_address
        self.last_sync_block = last_sync_block

        try:
            self.asset = self.es_instance.read(self.did)
        except Exception:
            logger.debug(f"Asset {self.did} is missing from ES.")
            self.asset = None

    def process(self):
        if not self.asset:
            return
        logger.debug(f"Retrieving number of orders for {self.token_address}.")
        number_orders, price = get_number_orders_price(
            self.token_address, self.last_sync_block, self.chain_id
        )
        self.asset["stats"]["orders"] = number_orders
        self.asset["stats"]["price"] = price

        logger.debug(f"Updating number of orders to {number_orders} for {self.did}.")
        self.es_instance.update(self.asset, self.did)

        return self.asset


class TokenURIUpdatedProcessor:
    def __init__(self, event, web3, es_instance, chain_id):
        self.did = make_did(event.address, chain_id)
        self.es_instance = es_instance
        self.event = event
        self.web3 = web3

        try:
            self.asset = self.es_instance.read(self.did)
        except Exception:
            self.asset = None

    def process(self):
        if not self.asset:
            return
        erc721_contract = get_nft_contract(self.web3, self.event.address)

        receipt = self.web3.eth.get_transaction_receipt(self.event.transactionHash)
        event_decoded = erc721_contract.events.TokenURIUpdate().process_receipt(
            receipt, errors=DISCARD
        )[0]

        self.asset["nft"]["tokenURI"] = event_decoded.args.tokenURI
        self.es_instance.update(self.asset, self.did)

        return self.asset


class MetadataStateProcessor(EventProcessor):
    def restore_ddo(self):
        soft_deleted_ddo = self._es_instance.read(self.did)

        receipt = self._web3.eth.get_transaction_receipt(
            soft_deleted_ddo["event"]["tx"]
        )

        create_events = self.dt_contract.events[
            EventTypes.EVENT_METADATA_CREATED
        ]().process_receipt(receipt, errors=DISCARD)
        update_events = self.dt_contract.events[
            EventTypes.EVENT_METADATA_UPDATED
        ]().process_receipt(receipt, errors=DISCARD)

        if not create_events and not update_events:
            logger.error("create/update ddo event not found")
            return False

        event = create_events[0] if create_events else update_events[0]

        event_processor = MetadataCreatedProcessor(
            event,
            self.dt_contract,
            self.sender_address,
            self._es_instance,
            self._web3,
            self.allowed_publishers,
            self.purgatory,
            self._chain_id,
        )

        return event_processor.process()

    def process(self):
        self.did = make_did(self.event.address, self._chain_id)
        # check if assets exists. if not, bail out
        exists = self._es_instance.exists(self.did)
        if not exists:
            logger.warn(
                f"Detected MetadataState changed for {self.did}, but it does not exists."
            )
            return
        if self.event.args.state == MetadataStates.ACTIVE:
            return self.restore_ddo()

        target_state = self.event.args.state
        if target_state in [
            MetadataStates.END_OF_LIFE,
            MetadataStates.DEPRECATED,
            MetadataStates.REVOKED,
        ]:
            try:
                self.soft_delete_ddo(self.did)
            except Exception:
                return

        self.update_aqua_nft_state_data(self.event.args.state, self.did)
