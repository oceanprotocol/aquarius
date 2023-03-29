#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import hashlib
import json
import lzma
import os
import uuid

import requests
from eth_account import Account
from web3 import Web3
from web3.datastructures import AttributeDict
from eth_utils.address import to_checksum_address

from aquarius.app.util import get_signature_vrs
from aquarius.events.constants import EventTypes
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.events.util import deploy_datatoken, make_did, get_nft_contract
from tests.ddos.ddo_event_sample_v4 import ddo_event_sample_v4
from web3.logs import DISCARD


rpc = os.environ.get("EVENTS_RPC", "")
provider = get_web3_connection_provider(rpc)
WEB3_INSTANCE = Web3(provider)


test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
test_account2 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY2", None))
test_account3 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY3", None))


def get_web3():
    return WEB3_INSTANCE


def new_ddo(account, web3, name, ddo=None):
    _ddo = ddo if ddo else ddo_event_sample_v4.copy()
    if "publicKey" not in _ddo or not _ddo["publicKey"]:
        _ddo["publicKey"] = [{"owner": ""}]
    _ddo["publicKey"][0]["owner"] = account.address
    _ddo["random"] = str(uuid.uuid4())
    dt_address = deploy_datatoken(web3, account, name, name)
    chain_id = web3.eth.chain_id
    _ddo["id"] = make_did(dt_address, chain_id)
    _ddo["chainId"] = chain_id
    _ddo["nftAddress"] = dt_address
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


def publish_ddo(client, base_ddo_url, events_object):
    ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = ddo.id
    send_create_update_tx("create", ddo, bytes([0]), test_account1)
    events_object.process_current_blocks()

    return did


def send_create_update_tx(name, ddo, flags, account):
    provider_url = "http://172.15.0.4:8030"
    provider_address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    datatoken_address = ddo["nftAddress"]

    web3 = get_web3()
    web3.eth.default_account = account.address

    event_name = (
        EventTypes.EVENT_METADATA_CREATED
        if name == "create"
        else EventTypes.EVENT_METADATA_UPDATED
    )

    dt_contract = get_nft_contract(get_web3(), datatoken_address)

    cap = web3.to_wei(100000, "ether")
    erc20_txn = dt_contract.functions.createERC20(
        1,
        ["ERC20DT1", "ERC20DT1Symbol"],
        [
            to_checksum_address(account.address),
            to_checksum_address(account.address),
            to_checksum_address(account.address),
            "0x0000000000000000000000000000000000000000",
        ],
        [cap, 0],
        [b""],
    ).transact()
    _ = get_web3().eth.wait_for_transaction_receipt(erc20_txn)
    erc20_address = dt_contract.caller.getTokensList()[0]

    for i in range(len(ddo.get("services", []))):
        ddo["services"][i]["datatokenAddress"] = erc20_address

    document = json.dumps(dict(ddo))
    if flags[0] & 1:
        compressed_document = lzma.compress(document.encode("utf-8"))
    else:
        compressed_document = document.encode("utf-8")

    if flags[0] & 2:
        headers = {"Content-type": "application/octet-stream"}
        response = requests.post(
            provider_url + "/api/services/encrypt?chainId={web3.chain_id}",
            data=compressed_document,
            headers=headers,
            timeout=5,
        )
        encrypted_data = response.text
    else:
        encrypted_data = compressed_document

    dataHash = hashlib.sha256(document.encode("UTF-8")).hexdigest()

    validatorContent = get_signature_vrs(document.encode("UTF-8"))
    validatorContent = (
        validatorContent["publicKey"],
        validatorContent["v"],
        validatorContent["r"][0],
        validatorContent["s"][0],
    )

    web3.strict_bytes_type_checking = False
    txn_hash = dt_contract.functions.setMetaData(
        0,
        provider_url,
        to_checksum_address(provider_address),
        flags,
        encrypted_data,
        dataHash,
        [validatorContent],
    ).transact()
    txn_receipt = get_web3().eth.wait_for_transaction_receipt(txn_hash)

    _ = getattr(dt_contract.events, event_name)().process_receipt(
        txn_receipt, errors=DISCARD
    )

    return txn_receipt, dt_contract, erc20_address


def send_set_metadata_state_tx(ddo, account, state):
    datatoken_address = ddo["nftAddress"]

    web3 = get_web3()
    web3.eth.default_account = to_checksum_address(account.address)

    dt_contract = get_nft_contract(web3, datatoken_address)

    txn_hash = dt_contract.functions.setMetaDataState(state).transact()
    txn_receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

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


def run_request_octet(client_method, url, data=None):
    if data is None:
        return client_method(url, content_type="application/octet-stream")

    return client_method(url, data=data, content_type="application/octet-stream")
