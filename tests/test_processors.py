#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import patch, Mock

from eth_account import Account
import os
import pytest
from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
    OrderStartedProcessor,
)
from aquarius.events.util import (
    setup_web3,
    deploy_datatoken,
    get_nft_contract,
)
from aquarius.myapp import app
from tests.helpers import get_ddo, new_ddo, send_create_update_tx, test_account1

event_sample = AttributeDict(
    {
        "args": AttributeDict(
            {
                "dataToken": "0xe22570D8ea2D8004023A928FbEb36f14738C62c9",
                "createdBy": "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260",
                "flags": b"\x00",
                "data": "",
                "decryptorUrl": "http://172.15.0.4:8030",
            }
        ),
        "event": "MetadataCreated",
        "logIndex": 0,
        "transactionIndex": 0,
        "transactionHash": HexBytes(
            "0x89b2570f115111d7be90da06adb76e594509f41a305ee415d5fc5e0eccabd2da"
        ),
        "address": "0x2cd82B786608998a331FF1aaE67B4b38d804635b",
        "blockHash": HexBytes(
            "0x06ce53546d23511f7437ec06d6aa3e9269c5ddc52ef3da712b0ce2a645b28501"
        ),
        "blockNumber": 410,
    }
)

event_updated_sample = AttributeDict(
    {
        "args": AttributeDict(
            {
                "dataToken": "0x2E6B0Ee23E8E15482117045a1410ed74AC5BBFE5",
                "updatedBy": "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260",
                "flags": b"\x00",
                "data": "",
                "decryptorUrl": "http://172.15.0.4:8030",
            }
        ),
        "event": "MetadataUpdated",
        "logIndex": 0,
        "transactionIndex": 0,
        "transactionHash": HexBytes(
            "0x2c658f33d5fbd53689834831e1c2aedf04b649bca397a3c46d5c283e735dc019"
        ),
        "address": "0x2cd82B786608998a331FF1aaE67B4b38d804635b",
        "blockHash": HexBytes(
            "0xac74047aa002d2c78e10c21d4f6193cdd28c4562f834ab7dbdd47535943554ff"
        ),
        "blockNumber": 492,
    }
)


def test_check_permission(monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "http://rbac")
    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, None, None, None, None
    )
    with patch("requests.post") as mock:
        mock.side_effect = Exception("Boom!")
        assert processor.check_permission("some_address") is False

    # will affect the process() function too
    with pytest.raises(Exception):
        with patch("requests.post") as mock:
            mock.side_effect = Exception("Boom!")
            processor.process()

    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, None, None, None, None, None, None
    )
    # will affect the process() function too
    with pytest.raises(Exception):
        with patch("requests.post") as mock:
            mock.side_effect = Exception("Boom!")
            processor.process()


def test_is_publisher_allowed():
    web3 = setup_web3()
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None, None
    )
    processor.allowed_publishers = None
    assert processor.is_publisher_allowed(processor.sender_address) is True


def test_process_fallback(monkeypatch, client, base_ddo_url, events_object):
    web3 = setup_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id
    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did

    events_object._es_instance.delete(did)

    _ddo["metadata"]["name"] = "Updated ddo by event"
    send_create_update_tx("update", _ddo, bytes(2), test_account1)

    # falls back on the MetadataCreatedProcessor
    # since no es instance means read will throw an Exception
    with patch("aquarius.events.processors.MetadataCreatedProcessor.process") as mock:
        events_object.process_current_blocks()
        mock.assert_called()


def test_do_decode_update():
    web3 = setup_web3()
    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, web3, None, None, None, None, None
    )

    processor.block = 0
    old_asset = {
        "event": {"block": 100, "tx": "placeholder"},
        "publicKey": [{"owner": "some_address"}],
    }
    assert processor.check_update(None, old_asset, "") is False


def test_missing_attributes():
    web3 = setup_web3()

    test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
    dt_address = deploy_datatoken(web3, test_account1, "TT1", "TT1Symbol")
    dt_contract = get_nft_contract(web3, dt_address)

    dt_factory = Mock()
    dt_factory.caller = Mock()
    dt_factory.caller.erc721List.return_value = (
        "0x0000000000000000000000000000000000000000"
    )

    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, web3, None, None, None
    )

    assert processor._get_contract_attribute(dt_contract, "non_existent") == ""
    assert processor._get_contract_attribute(dt_contract, "symbol") == "TT1Symbol"

    processor.dt_contract = Mock(spec=dt_contract)
    processor.caller = Mock()
    processor.caller.ownerOf.side_effect = Exception()

    processor.event = Mock()
    processor.event.args.decryptorUrl = ""
    processor.event.args.metaDataHash = ""
    processor.event.args.address = ""
    processor.event.address = "0x0000000000000000000000000000000000000000"

    with patch("aquarius.events.processors.decrypt_ddo") as mock:
        mock.side_effect = Exception("in decrypt_ddo: some message")
        with patch("aquarius.events.processors.get_dt_factory") as mock2:
            mock2.return_value = dt_factory
            with pytest.raises(Exception, match="in decrypt_ddo: some message"):
                processor.process()

    processor = MetadataUpdatedProcessor(
        event_sample, None, None, None, web3, None, None, None
    )

    assert processor._get_contract_attribute(dt_contract, "non_existent") == ""
    assert processor._get_contract_attribute(dt_contract, "symbol") == "TT1Symbol"

    processor.dt_contract = Mock(spec=dt_contract)
    processor.caller = Mock()
    processor.caller.ownerOf.side_effect = Exception()

    processor.event = Mock()
    processor.event.args.decryptorUrl = ""
    processor.event.args.metaDataHash = ""
    processor.event.address = "0x0000000000000000000000000000000000000000"

    with patch("aquarius.events.processors.decrypt_ddo") as mock:
        mock.side_effect = Exception("in decrypt_ddo: some message")
        with patch("aquarius.events.processors.get_dt_factory") as mock2:
            mock2.return_value = dt_factory
            with pytest.raises(Exception, match="in decrypt_ddo: some message"):
                processor.process()


def test_drop_non_factory():
    dt_factory = Mock()
    dt_factory.caller = Mock()
    dt_factory.caller.erc721List.return_value = "not the address"

    web3 = setup_web3()

    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, web3, None, None, None
    )

    with patch("aquarius.events.processors.get_dt_factory") as mock2:
        mock2.return_value = dt_factory
        assert not processor.process()


def test_order_started_processor():
    web3 = setup_web3()

    test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
    dt_address = deploy_datatoken(web3, test_account1, "TT1", "TT1Symbol")

    es_instance = Mock()
    es_instance.read.return_value = {"sample_asset": "mock", "stats": {"orders": 0}}
    es_instance.update.return_value = None

    price_json = {"value": 12.4, "tokenAddress": "test", "tokenSymbol": "test2"}

    processor = OrderStartedProcessor(dt_address, es_instance, 0, 0)
    with patch("aquarius.events.processors.get_number_orders_price") as no_mock:
        no_mock.return_value = 3, price_json
        updated_asset = processor.process()

    assert es_instance.update.called_once()
    assert updated_asset["stats"]["orders"] == 3
    assert updated_asset["stats"]["price"] == price_json


def test_order_started_processor_no_asset():
    web3 = setup_web3()

    test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
    dt_address = deploy_datatoken(web3, test_account1, "TT1", "TT1Symbol")

    es_instance = Mock()
    es_instance.read.return_value = None

    processor = OrderStartedProcessor(dt_address, es_instance, 0, 0)
    updated_asset = processor.process()

    assert not es_instance.update.called
    assert updated_asset is None
