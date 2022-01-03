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
import logging
import os
from web3.main import Web3

logger = logging.getLogger("aquarius")
keys = KeyAPI(NativeECCBackend)


def sanitize_record(data_record):
    if "_id" in data_record:
        data_record.pop("_id")

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


def get_timestamp():
    """Return the current system timestamp."""
    return f"{datetime.utcnow().replace(microsecond=0).isoformat()}Z"


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
        message = Web3.solidityKeccak(
            ["bytes", "bytes"],
            [Web3.toBytes(text=prefix), Web3.toBytes(hashed_raw.digest())],
        )
        signed = keys.ecdsa_sign(message_hash=message, private_key=keys_pk)

        values = {"hash": hashed_raw.hexdigest(), "publicKey": wallet.address}

        values["v"] = (signed.v + 27) if signed.v <= 1 else signed.v
        values["r"] = (Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")),)
        values["s"] = (Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")),)
    except AquariusPrivateKeyException:
        values = {"hash": "", "publicKey": "", "r": "", "s": "", "v": ""}

    return values
