#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import hashlib
import json
import os
import requests
import time
import uuid

from jsonsempai import magic  # noqa: F401
from artifacts import ERC721Template
from eth_utils import remove_0x_prefix, add_0x_prefix
from web3 import Web3
from eth_account import Account
from web3.datastructures import AttributeDict

from aquarius.events.util import deploy_datatoken
from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from aquarius.events.http_provider import get_web3_connection_provider
from tests.ddos.ddo_event_sample import ddo_event_sample

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
    _ddo = ddo if ddo else ddo_event_sample.copy()
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


def get_event(event_name, block, did, timeout=45):
    did = prepare_did(did)
    start = time.time()
    f = getattr(get_metadata_contract(get_web3()).events, event_name)().createFilter(
        fromBlock=block
    )
    logs = []
    while not logs:
        logs = f.get_all_entries()
        if not logs:
            time.sleep(0.2)

        if time.time() - start > timeout:
            break

    assert logs, f"no events found {event_name}, block {block}."
    print(
        f"done waiting for {event_name} event, got {len(logs)} logs, and datatokens: {[l.args.dataToken for l in logs]}"
    )
    _log = None
    for log in logs:
        if log.args.dataToken == did:
            _log = log
            break
    assert _log, f"event log not found: {event_name}, {block}, {did}"
    return _log


def send_create_update_tx(name, ddo, flags, account):
    # TODO: replace with actual defaults
    provider_url = 'http://localhost:8030'
    provider_address = 'TEST'
    did = ddo.id
    datatoken_address = ddo["dataToken"]
    aquarius_account = Account.from_key(os.environ.get("PRIVATE_KEY"))
    document = json.dumps(dict(ddo))
    data = {
        "document": document,
        "documentId": did,
        "publisherAddress": aquarius_account.address
    }
    response = requests.post(provider_url + '/api/v1/services/encryptDDO', json=data)
    encrypted_data = response.content
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

    dt_contract = get_web3().eth.contract(abi=ERC721Template.abi, address=datatoken_address)
    txn_hash = dt_contract.functions.setMetaData(
        0, provider_url, provider_address, flags, encrypted_data, dataHash
    ).transact()
    txn_receipt = get_web3().eth.wait_for_transaction_receipt(txn_hash)

    # TODO: change this to the proper processReceipt, event name is not relevant anymore
    # and we can even remove it
    _ = getattr(dt_contract.events, event_name)().processReceipt(
        txn_receipt
    )
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
