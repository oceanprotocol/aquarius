#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime
from eth_account import Account
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from hashlib import sha256
import json
from json import JSONDecodeError
import logging
import os
import requests
from web3.main import Web3

from aquarius.app.auth_util import sanitize_addresses

logger = logging.getLogger("aquarius")
keys = KeyAPI(NativeECCBackend)


def sanitize_record(data_record):
    if "_id" in data_record:
        data_record.pop("_id")

    if os.getenv("RBAC_SERVER_URL"):
        payload = {
            "eventType": "filter_single_result",
            "component": "metadatacache",
            "ddo": data_record,
        }

        return requests.post(os.getenv("RBAC_SERVER_URL"), json=payload).json()

    return json.dumps(data_record, default=datetime_converter)


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
        signable_hash = Web3.solidityKeccak(
            ["bytes", "bytes"],
            [Web3.toBytes(text=prefix), Web3.toBytes(hashed_raw.digest())],
        )
        signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=keys_pk)

        values = {"hash": "0x" + hashed_raw.hexdigest(), "publicKey": wallet.address}

        values["v"] = (signed.v + 27) if signed.v <= 1 else signed.v
        values["r"] = (Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")),)
        values["s"] = (Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")),)
    except AquariusPrivateKeyException:
        values = {"hash": "", "publicKey": "", "r": "", "s": "", "v": ""}

    return values


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
