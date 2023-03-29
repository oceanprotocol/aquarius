#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os

from datetime import datetime
from hashlib import sha256
from json import JSONDecodeError

from eth_account import Account
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from web3.main import Web3

from aquarius.app.auth_util import sanitize_addresses
from aquarius.rbac import RBAC

logger = logging.getLogger("aquarius")
keys = KeyAPI(NativeECCBackend)


def sanitize_record(data_record):
    if "_id" in data_record:
        data_record.pop("_id")

    if not os.getenv("RBAC_SERVER_URL"):
        return json.dumps(data_record, default=datetime_converter)

    return json.dumps(RBAC.sanitize_record(data_record))


def sanitize_query_result(query_result):
    if not os.getenv("RBAC_SERVER_URL"):
        return query_result

    return RBAC.sanitize_query_result(query_result)


def get_bool_env_value(envvar_name, default_value=0):
    assert default_value in (0, 1), "bad default value, must be either 0 or 1"
    try:
        return bool(int(os.getenv(envvar_name, default_value)))
    except Exception:
        return bool(default_value)


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()


class AquariusPrivateKeyException(Exception):
    pass


def get_aquarius_wallet():
    pk = os.environ.get("PRIVATE_KEY", None)
    if pk is None:
        raise AquariusPrivateKeyException("Missing Aquarius PRIVATE_KEY")

    return Account.from_key(private_key=pk)


def get_signature_vrs(raw):
    try:
        hashed_raw = sha256(raw)
        wallet = get_aquarius_wallet()

        keys_pk = keys.PrivateKey(wallet.key)

        prefix = "\x19Ethereum Signed Message:\n32"
        signable_hash = Web3.solidity_keccak(
            ["bytes", "bytes"],
            [Web3.to_bytes(text=prefix), Web3.to_bytes(hashed_raw.digest())],
        )
        signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=keys_pk)

        values = {"hash": "0x" + hashed_raw.hexdigest(), "publicKey": wallet.address}

        values["v"] = (signed.v + 27) if signed.v <= 1 else signed.v
        values["r"] = (Web3.to_hex(Web3.to_bytes(signed.r).rjust(32, b"\0")),)
        values["s"] = (Web3.to_hex(Web3.to_bytes(signed.s).rjust(32, b"\0")),)
    except AquariusPrivateKeyException:
        values = {"hash": "", "publicKey": "", "r": "", "s": "", "v": ""}

    return values


def get_signature_bytes(raw):
    try:
        wallet = get_aquarius_wallet()

        keys_pk = keys.PrivateKey(wallet.key)
        message_hash = Web3.solidity_keccak(
            ["bytes"],
            [Web3.to_bytes(text=raw)],
        )
        prefix = "\x19Ethereum Signed Message:\n32"
        signable_hash = Web3.solidity_keccak(
            ["bytes", "bytes"],
            [Web3.to_bytes(text=prefix), Web3.to_bytes(message_hash)],
        )
        signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=keys_pk)
        v = str(Web3.to_hex(Web3.to_bytes(signed.v)))
        r = str(Web3.to_hex(Web3.to_bytes(signed.r).rjust(32, b"\0")))
        s = str(Web3.to_hex(Web3.to_bytes(signed.s).rjust(32, b"\0")))
        signature = "0x" + r[2:] + s[2:] + v[2:]
    except AquariusPrivateKeyException:
        signature = None

    return signature


def get_allowed_publishers():
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

    return set(sanitize_addresses(allowed_publishers))


def get_did_state(es_instance, chain_id, nft, tx_id, did):
    if any([chain_id, nft, did, tx_id]):
        conditions = []
        if chain_id:
            conditions.append({"term": {"chain_id": chain_id}})
        if nft:
            conditions.append({"match": {"nft": nft}})
        if tx_id:
            conditions.append({"match": {"tx_id": tx_id}})
        if did:
            conditions.append({"term": {"_id": did}})
        q = {"bool": {"filter": conditions}}
    else:
        q = {"match_all": {}}
    return es_instance.es.search(index=es_instance._did_states_index, query=q)


def get_retry_queue(es_instance, chain_id, nft, did, retry_type):
    if any([chain_id, nft, did, retry_type]):
        conditions = []
        if chain_id:
            conditions.append({"term": {"chain_id": chain_id}})
        if nft:
            conditions.append({"match": {"nft_address": nft}})
        if did:
            conditions.append({"term": {"did": did}})
        if retry_type:
            conditions.append({"term": {"type": retry_type}})
        q = {"bool": {"filter": conditions}}
    else:
        q = {"match_all": {}}
    return es_instance.es.search(
        index=f"{es_instance.db_index}_retries", query=q, from_=0, size=10000
    )
