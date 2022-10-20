#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import threading
import time
from datetime import timedelta
from unittest.mock import patch

import elasticsearch
import pytest
from artifacts import ERC20Template, ERC721Template, FixedRateExchange
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from jsonsempai import magic  # noqa: F401
from web3.main import Web3

from aquarius.app.util import get_aquarius_wallet
from aquarius.config import get_version
from aquarius.events.constants import AquariusCustomDDOFields, MetadataStates
from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.util import get_address_file, get_fre, setup_web3
from aquarius.myapp import app
from tests.helpers import (
    get_ddo,
    get_web3,
    new_ddo,
    run_request_get_data,
    send_create_update_tx,
    send_set_metadata_state_tx,
    test_account1,
    test_account2,
    test_account3,
)

keys = KeyAPI(NativeECCBackend)

logger = logging.getLogger("aquarius")


def run_test(client, base_ddo_url, events_instance, flags):
    web3 = events_instance._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, _, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([flags]), test_account1
    )
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    for service in published_ddo["services"]:
        assert service["datatokenAddress"] == erc20_address
        assert service["name"] in ["dataAssetAccess", "dataAssetComputingService"]

    _ddo["metadata"]["name"] = "Updated ddo by event"
    send_create_update_tx("update", _ddo, bytes([flags]), test_account1)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["metadata"]["name"] == "Updated ddo by event"


def test_publish_and_update_ddo(client, base_ddo_url, events_object, monkeypatch):
    aqua_address = get_aquarius_wallet().address
    monkeypatch.setenv("ALLOWED_VALIDATORS", f'["{aqua_address}"]')
    run_test(client, base_ddo_url, events_object, 2)


def test_publish_and_update_ddo_with_lzma(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 1)


def test_publish_and_update_ddo_with_lzma_and_encrypt(
    client, base_ddo_url, events_object
):
    run_test(client, base_ddo_url, events_object, 3)


def test_publish_and_update_ddo_unencrypted(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 0)


def test_publish(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["chainId"] == get_web3().eth.chain_id


def test_publish_unallowed_address(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account3, get_web3(), "dt.0")
    did = _ddo.id
    send_create_update_tx("create", _ddo, bytes([2]), test_account3)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["error"] == f"Asset DID {did} not found in Elasticsearch."


def test_publish_and_update_ddo_rbac(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "http://localhost:3000")
    run_test(client, base_ddo_url, events_object, 2)


def test_get_chains_list(client, chains_url):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    rv = client.get(chains_url + "/list", content_type="application/json")
    chains_list = json.loads(rv.data.decode("utf-8"))
    assert chains_list
    assert chains_list[str(chain_id)]


def test_get_chain_status(client, chains_url):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    rv = client.get(
        chains_url + f"/status/{str(chain_id)}", content_type="application/json"
    )
    chain_status = json.loads(rv.data.decode("utf-8"))
    assert int(chain_status["last_block"]) > 0
    assert chain_status["version"] == get_version()


def test_get_assets_in_chain(client, events_object):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    res = events_object.get_assets_in_chain()
    assert set([item["chainId"] for item in res]) == {chain_id}


def test_events_monitor_object(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monkeypatch.setenv("ALLOWED_PUBLISHERS", "can not be converted to a set")
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor._allowed_publishers == set()

    monkeypatch.setenv("OCN_EVENTS_MONITOR_QUITE_TIME", "can not be converted to int")
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor._monitor_sleep_time == 10

    monkeypatch.setenv("EVENTS_CLEAN_START", "1")
    with patch("aquarius.events.events_monitor.EventsMonitor.reset_chain") as mock:
        monitor = EventsMonitor(setup_web3(config_file), config_file)
        mock.assert_called_once()


def test_start_stop_events_monitor():
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)

    monitor._monitor_is_on = True
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor._contract_address = None
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor._contract = None
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    with patch("aquarius.events.events_monitor.Thread.start") as mock:
        monitor.start_events_monitor()
        mock.assert_called_once()

    monitor.stop_monitor()


def test_process_block_range(client, base_ddo_url, events_object):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor.process_block_range(13, 10) is None  # not processing if from > to

    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    send_create_update_tx("create", _ddo, bytes([2]), test_account1)

    with patch(
        "aquarius.events.events_monitor.MetadataCreatedProcessor.process"
    ) as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.process_current_blocks() is None

    send_create_update_tx("update", _ddo, bytes([2]), test_account1)
    with patch(
        "aquarius.events.events_monitor.MetadataUpdatedProcessor.process"
    ) as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.process_current_blocks() is None


def test_elasticsearch_connection(events_object, caplog):
    with patch("elasticsearch.Elasticsearch.ping") as es_mock:
        es_mock.return_value = True
        with patch("elasticsearch.Elasticsearch.get") as mock:
            mock.return_value = {"_source": {"last_block": 24}}
            assert events_object.get_last_processed_block() == 24

    with patch("elasticsearch.Elasticsearch.ping") as es_mock:
        es_mock.return_value = False
        action_thread = threading.Thread(target=events_object.get_last_processed_block)
        action_thread.start()
        time.sleep(5)
        es_mock.return_value = True
        action_thread.join()
        assert "Connection to ES failed. Trying to connect to back..." in caplog.text
        assert "Stable connection to ES." in caplog.text


def test_get_last_processed_block(events_object, monkeypatch):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = elasticsearch.NotFoundError("Boom!")
        assert events_object.get_last_processed_block() == int(
            os.getenv("BFACTORY_BLOCK")
        )

    intended_block = -10  # can not be smaller than start block
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.return_value = {"_source": {"last_block": intended_block}}
        assert events_object.get_last_processed_block() == 0

    monkeypatch.delenv("BFACTORY_BLOCK")
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = elasticsearch.NotFoundError("Boom!")
        assert (
            events_object.get_last_processed_block() == 5
        )  # startBlock from address.json for ganache


def test_store_last_processed_block(events_object):
    block = events_object.get_last_processed_block() + 10
    with patch("elasticsearch.Elasticsearch.index") as mock:
        mock.side_effect = elasticsearch.exceptions.RequestError("Boom!")
        assert events_object.store_last_processed_block(block) is None


def test_add_chain_id_to_chains_list(events_object):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.add_chain_id_to_chains_list() is None

    with patch("elasticsearch.Elasticsearch.index") as mock:
        mock.side_effect = elasticsearch.exceptions.RequestError("Boom!")
        events_object.add_chain_id_to_chains_list()
        assert events_object.add_chain_id_to_chains_list() is None


def test_get_event_logs(events_object):
    assert events_object.get_event_logs("NonExistentEvent", 0, 10) == []


def test_order_started(events_object, client, base_ddo_url):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.process_current_blocks()
    token_contract = web3.eth.contract(
        abi=ERC20Template.abi, address=web3.toChecksumAddress(erc20_address)
    )

    token_contract.functions.mint(
        web3.toChecksumAddress(test_account3.address), web3.toWei(10, "ether")
    ).transact({"from": test_account1.address})
    # mock provider fees
    provider_wallet = get_aquarius_wallet()
    provider_fee_amount = 0
    provider_data = json.dumps({"timeout": 0}, separators=(",", ":"))
    provider_fee_address = provider_wallet.address
    provider_fee_token = "0x0000000000000000000000000000000000000000"
    message_hash = Web3.solidityKeccak(
        ["bytes", "address", "address", "uint256", "uint256"],
        [
            Web3.toHex(Web3.toBytes(text=provider_data)),
            provider_fee_address,
            provider_fee_token,
            provider_fee_amount,
            0,
        ],
    )
    pk = keys.PrivateKey(provider_wallet.key)
    prefix = "\x19Ethereum Signed Message:\n32"
    signable_hash = Web3.solidityKeccak(
        ["bytes", "bytes"], [Web3.toBytes(text=prefix), Web3.toBytes(message_hash)]
    )
    signed = keys.ecdsa_sign(message_hash=signable_hash, private_key=pk)

    provider_fee = {
        "providerFeeAddress": web3.toChecksumAddress(provider_fee_address),
        "providerFeeToken": web3.toChecksumAddress(provider_fee_token),
        "providerFeeAmount": provider_fee_amount,
        "providerData": Web3.toHex(Web3.toBytes(text=provider_data)),
        # make it compatible with last openzepellin https://github.com/OpenZeppelin/openzeppelin-contracts/pull/1622
        "v": (signed.v + 27) if signed.v <= 1 else signed.v,
        "r": Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")),
        "s": Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")),
        "validUntil": 0,
    }
    txn = token_contract.functions.startOrder(
        web3.toChecksumAddress(test_account3.address),
        1,
        (
            web3.toChecksumAddress(provider_fee["providerFeeAddress"]),
            web3.toChecksumAddress(provider_fee["providerFeeToken"]),
            provider_fee["providerFeeAmount"],
            provider_fee["v"],
            provider_fee["r"],
            provider_fee["s"],
            provider_fee["validUntil"],
            provider_fee["providerData"],
        ),
        (
            "0x0000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000000",
            0,
        ),
    ).transact({"from": test_account3.address})
    web3.eth.wait_for_transaction_receipt(txn)
    events_object.process_current_blocks()

    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["orders"] == 1


def test_metadata_state_update(client, base_ddo_url, events_object):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    initial_ddo = get_ddo(client, base_ddo_url, did)
    assert initial_ddo["id"] == did

    # MetadataState updated to other than active should soft delete the ddo from elasticsearch
    send_set_metadata_state_tx(
        ddo=_ddo, account=test_account1, state=MetadataStates.DEPRECATED
    )
    events_object.process_current_blocks()
    time.sleep(30)
    published_ddo = get_ddo(client, base_ddo_url, did)
    # Check if asset is soft deleted
    assert "id" not in published_ddo
    assert list(published_ddo.keys()) == AquariusCustomDDOFields.get_all_values()
    assert (
        published_ddo[AquariusCustomDDOFields.EVENT]["tx"]
        == initial_ddo[AquariusCustomDDOFields.EVENT]["tx"]
    )
    assert (
        published_ddo[AquariusCustomDDOFields.NFT]["state"] == MetadataStates.DEPRECATED
    )

    # MetadataState updated to active should delegate to MetadataCreated processor
    # and recreate asset
    send_set_metadata_state_tx(
        ddo=_ddo, account=test_account1, state=MetadataStates.ACTIVE
    )
    events_object.process_current_blocks()
    time.sleep(30)
    published_ddo = get_ddo(client, base_ddo_url, did)
    # Asset has been recreated
    assert published_ddo["id"] == did
    # The event after recreation is kept as it uses the same original creation event
    assert published_ddo["event"]["tx"] == initial_ddo["event"]["tx"]
    # The NFT state is active
    assert published_ddo[AquariusCustomDDOFields.NFT]["state"] == MetadataStates.ACTIVE

    # MetadataState updated to order disabled should leave the contents intact
    # but change the state
    send_set_metadata_state_tx(
        ddo=_ddo, account=test_account1, state=MetadataStates.ORDERING_DISABLED
    )
    events_object.process_current_blocks()
    time.sleep(30)
    published_ddo = get_ddo(client, base_ddo_url, did)
    # Asset id and event are untouched
    assert published_ddo["id"] == did
    assert published_ddo["event"]["tx"] == initial_ddo["event"]["tx"]
    # The NFT state is disabled
    assert (
        published_ddo[AquariusCustomDDOFields.NFT]["state"]
        == MetadataStates.ORDERING_DISABLED
    )

    # MetadataState updated to active should delegate to MetadataCreated processor
    # and reactivate the existing asset
    send_set_metadata_state_tx(
        ddo=_ddo, account=test_account1, state=MetadataStates.ACTIVE
    )
    events_object.process_current_blocks()
    time.sleep(30)
    published_ddo = get_ddo(client, base_ddo_url, did)
    # Existing asset has been reactivated
    assert published_ddo["id"] == did
    # The event after reactivated is kept as it uses the same original creation event
    assert published_ddo["event"]["tx"] == initial_ddo["event"]["tx"]
    # The NFT state is active
    assert published_ddo[AquariusCustomDDOFields.NFT]["state"] == MetadataStates.ACTIVE


def test_token_uri_update(client, base_ddo_url, events_object):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    initial_ddo = get_ddo(client, base_ddo_url, did)
    assert initial_ddo["id"] == did
    assert initial_ddo["nft"]["tokenURI"] == "http://oceanprotocol.com/nft"

    nft_contract = web3.eth.contract(
        abi=ERC721Template.abi,
        address=web3.toChecksumAddress(initial_ddo["nftAddress"]),
    )

    web3.eth.default_account = test_account1.address
    txn_hash = nft_contract.functions.setTokenURI(
        1, "http://something-else.com"
    ).transact()
    _ = web3.eth.wait_for_transaction_receipt(txn_hash)

    events_object.process_current_blocks()
    updated_ddo = get_ddo(client, base_ddo_url, did)
    assert updated_ddo["id"] == did
    assert updated_ddo["nft"]["tokenURI"] == "http://something-else.com"


def test_token_transfer(client, base_ddo_url, events_object):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    initial_ddo = get_ddo(client, base_ddo_url, did)
    assert initial_ddo["id"] == did
    assert initial_ddo["nft"]["owner"] == test_account1.address

    nft_contract = web3.eth.contract(
        abi=ERC721Template.abi,
        address=web3.toChecksumAddress(initial_ddo["nftAddress"]),
    )

    web3.eth.default_account = test_account1.address
    txn_hash = nft_contract.functions.safeTransferFrom(
        test_account1.address, test_account2.address, 1
    ).transact()
    _ = web3.eth.wait_for_transaction_receipt(txn_hash)

    events_object.process_current_blocks()
    updated_ddo = get_ddo(client, base_ddo_url, did)
    assert updated_ddo["id"] == did
    assert updated_ddo["nft"]["owner"] == test_account2.address


def test_trigger_caching(client, base_ddo_url, events_object):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    txn_receipt, _, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    tx_id = txn_receipt["transactionHash"].hex()

    with patch("aquarius.app.es_instance.ElasticsearchInstance.get") as mock:
        mock.side_effect = Exception("Boom!")
        response = run_request_get_data(
            client.post, "api/aquarius/assets/triggerCaching", {"transactionId": tx_id}
        )
        assert response["error"] == "new exception in processor, retry again"

    response = run_request_get_data(
        client.post, "api/aquarius/assets/triggerCaching", {"transactionId": tx_id}
    )
    assert response["id"] == did

    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    for service in published_ddo["services"]:
        assert service["datatokenAddress"] == erc20_address
        assert service["name"] in ["dataAssetAccess", "dataAssetComputingService"]

    _ddo["metadata"]["name"] = "Updated ddo by event"
    txn_receipt, dt_contract, _ = send_create_update_tx(
        "update", _ddo, bytes([2]), test_account1
    )
    tx_id = txn_receipt["transactionHash"].hex()

    response = run_request_get_data(
        client.post, "api/aquarius/assets/triggerCaching", {"transactionId": tx_id}
    )
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["metadata"]["name"] == "Updated ddo by event"

    assert response["metadata"]["name"] == "Updated ddo by event"

    # index out of range
    response = run_request_get_data(
        client.post,
        "api/aquarius/assets/triggerCaching",
        {"transactionId": tx_id, "logIndex": 2},
    )
    assert response["error"] == "Log index 2 not found"

    # can not find event created, nor event updated
    txn_hash = dt_contract.functions.setTokenURI(
        1, "http://something-else.com"
    ).transact()
    txn_receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
    tx_id = txn_receipt["transactionHash"].hex()
    response = run_request_get_data(
        client.post, "api/aquarius/assets/triggerCaching", {"transactionId": tx_id}
    )
    assert response["error"] == "No metadata created/updated event found in tx."


@pytest.mark.skip
def test_publish_error(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv("PROCESS_RETRY_QUEUE", "1")

    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    txn_receipt, _, _ = send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    tx_id = txn_receipt["transactionHash"].hex()
    # prevent any issues from previous tests, start clean-slate
    events_object.retry_mechanism.clear_all()
    events_object.retry_mechanism.retry_interval = timedelta(seconds=30)

    # force first trial to fail with decrypt exception
    with patch("aquarius.events.processors.decrypt_ddo") as mock:
        mock.side_effect = Exception("First exception")
        events_object.process_current_blocks()

    # the asset is not published
    ddo = get_ddo(client, base_ddo_url, did)
    assert ddo["error"] == f"Asset DID {did} not found in Elasticsearch."

    # later, that asset will be ripe and ready in the retry queue
    timeout = time.time() + 30 * 4
    job_is_valid = False
    while True:
        tx_ids = [
            res["_source"]["tx_id"]
            for res in events_object.retry_mechanism.get_from_retry_queue()
        ]
        if tx_id in tx_ids or time.time() > timeout:
            job_is_valid = True
            break

        time.sleep(1)

    assert job_is_valid, "tx id was not picked up"

    # no exceptions this time
    events_object.process_current_blocks()

    # asset is correctly published on retry
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did

    timeout = time.time() + 30 * 4
    job_is_done = False
    while True:
        tx_ids = [
            res["_source"]["tx_id"] for res in events_object.retry_mechanism.get_all()
        ]
        if tx_id not in tx_ids or time.time() > timeout:
            job_is_done = True
            break

        time.sleep(1)

    assert job_is_done, "tx id was not deleted from queue"


def test_exchange_created(events_object, client, base_ddo_url):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.process_current_blocks()
    token_contract = web3.eth.contract(
        abi=ERC20Template.abi, address=web3.toChecksumAddress(erc20_address)
    )

    amount = web3.toWei("100000", "ether")
    rate = web3.toWei("1", "ether")

    address_file = get_address_file()
    with open(address_file) as f:
        address_json = json.load(f)

    fre_address = address_json["development"]["FixedPrice"]

    token_contract.functions.mint(
        web3.toChecksumAddress(test_account3.address), amount
    ).transact({"from": test_account1.address})

    ocean_address = web3.toChecksumAddress(address_json["development"]["Ocean"])
    ocean_contract = web3.eth.contract(
        abi=ERC20Template.abi, address=web3.toChecksumAddress(ocean_address)
    )
    ocean_symbol = ocean_contract.caller.symbol()

    tx = token_contract.functions.createFixedRate(
        web3.toChecksumAddress(fre_address),
        [
            ocean_address,
            web3.toChecksumAddress(test_account1.address),
            "0x0000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000000",
        ],
        [
            18,
            18,
            rate,
            0,
            0,
        ],
    ).transact({"from": test_account1.address})
    receipt = web3.eth.wait_for_transaction_receipt(tx)
    events_object.process_current_blocks()

    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["price"] == {
        "tokenAddress": ocean_address,
        "tokenSymbol": ocean_symbol,
        "value": 1.0,
    }

    fre = get_fre(web3)
    rate = 2 * rate
    exchange_id = (
        fre.events.ExchangeCreated().processReceipt(receipt)[0].args.exchangeId
    )
    tx = fre.functions.setRate(exchange_id, rate).transact(
        {"from": test_account1.address}
    )
    receipt = web3.eth.wait_for_transaction_receipt(tx)
    events_object.process_current_blocks()

    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["price"] == {
        "tokenAddress": ocean_address,
        "tokenSymbol": ocean_symbol,
        "value": 2.0,
    }


def test_dispenser_created(events_object, client, base_ddo_url):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.process_current_blocks()
    token_contract = web3.eth.contract(
        abi=ERC20Template.abi, address=web3.toChecksumAddress(erc20_address)
    )

    address_file = get_address_file()
    with open(address_file) as f:
        address_json = json.load(f)

    dispenser_address = address_json["development"]["Dispenser"]

    tx = token_contract.functions.createDispenser(
        web3.toChecksumAddress(dispenser_address),
        web3.toWei("1", "ether"),
        web3.toWei("1", "ether"),
        True,
        "0x0000000000000000000000000000000000000000",
    ).transact({"from": test_account1.address})

    _ = web3.eth.wait_for_transaction_receipt(tx)
    events_object.process_current_blocks()

    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["price"] == {"value": 0.0}
