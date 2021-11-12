#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import hashlib
import json
import lzma
import os
import time
import uuid

import requests
from eth_account import Account
from eth_utils import add_0x_prefix, remove_0x_prefix
from jsonsempai import magic  # noqa: F401
from web3 import Web3
from web3.datastructures import AttributeDict

from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.events.util import deploy_datatoken
from artifacts import ERC721Template
from tests.ddos.ddo_event_sample_v4 import ddo_event_sample_v4

rpc = os.environ.get("EVENTS_RPC", "")
provider = get_web3_connection_provider(rpc)
WEB3_INSTANCE = Web3(provider)


test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
test_account2 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY2", None))
test_account3 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY3", None))


def get_web3():
    return WEB3_INSTANCE


def prepare_did(text):
    prefix = "did:op:"
    if text.startswith(prefix):
        text = text[len(prefix) :]
    return add_0x_prefix(text)


def new_did(dt_address):
    return f"did:op:{remove_0x_prefix(dt_address)}"


def new_ddo(account, web3, name, ddo=None):
    _ddo = ddo if ddo else ddo_event_sample_v4.copy()
    if "publicKey" not in _ddo or not _ddo["publicKey"]:
        _ddo["publicKey"] = [{"owner": ""}]
    _ddo["publicKey"][0]["owner"] = account.address
    _ddo["random"] = str(uuid.uuid4())
    dt_address = deploy_datatoken(web3, account, name, name)
    _ddo["id"] = new_did(dt_address)
    _ddo["dataToken"] = dt_address
    return AttributeDict(_ddo)


def get_ddo(client, base_ddo_url, did):
    rv = client.get(base_ddo_url + f"/{did}", content_type="application/json")
    try:
        fetched_ddo = json.loads(rv.data.decode("utf-8"))
        return fetched_ddo
    except (Exception, ValueError) as e:
        print(
            f"Error fetching cached ddo {did}: {e}." f"\nresponse data was: {rv.data}"
        )
        return None


def send_create_update_tx(name, ddo, flags, account):
    provider_url = "http://localhost:8030"
    provider_address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    did = ddo.id
    datatoken_address = ddo["dataToken"]
    document = json.dumps(dict(ddo))

    if flags[0] & 1:
        compressed_document = lzma.compress(document.encode("utf-8"))
    else:
        compressed_document = document.encode("utf-8")

    if flags[0] & 2:
        headers = {"Content-type": "application/octet-stream"}
        response = requests.post(
            provider_url + "/api/v1/services/encrypt",
            data=compressed_document,
            headers=headers,
        )
        encrypted_data = response.text
    else:
        encrypted_data = compressed_document

    dataHash = hashlib.sha256(document.encode("UTF-8")).hexdigest()

    print(f"{name}DDO {did} with flags: {flags} from {account.address}")
    did = prepare_did(did)
    print(
        "*****************************************************************************\r\n"
    )
    print(did)
    print(
        "*****************************************************************************\r\n"
    )

    web3 = get_web3()
    web3.eth.default_account = account.address

    event_name = EVENT_METADATA_CREATED if name == "create" else EVENT_METADATA_UPDATED

    dt_contract = get_web3().eth.contract(
        abi=ERC721Template.abi, address=datatoken_address
    )

    txn_hash = dt_contract.functions.setMetaData(
        0, provider_url, provider_address, flags, encrypted_data, dataHash
    ).transact()
    txn_receipt = get_web3().eth.wait_for_transaction_receipt(txn_hash)

    cap = web3.toWei(100000, "ether")
    erc20_txn = dt_contract.functions.createERC20(
        1,
        ["ERC20DT1", "ERC20DT1Symbol"],
        [
            account.address,
            account.address,
            account.address,
            "0x0000000000000000000000000000000000000000",
        ],
        [cap, 0],
        [b""],
    ).transact()
    _ = get_web3().eth.wait_for_transaction_receipt(erc20_txn)

    # TODO: change this to the proper processReceipt, event name is not relevant anymore
    # and we can even remove it
    _ = getattr(dt_contract.events, event_name)().processReceipt(txn_receipt)
    return txn_receipt


def run_request_get_data(client_method, url, data=None):
    _response = run_request(client_method, url, data)
    print(f"response: {_response}")
    if _response and _response.data:
        return json.loads(_response.data.decode("utf-8"))

    return None


def run_request(client_method, url, data=None):
    if data is None:
        _response = client_method(url, content_type="application/json")
    else:
        _response = client_method(
            url, data=json.dumps(data), content_type="application/json"
        )

    return _response
