import copy
import json
from hashlib import sha256
from unittest.mock import patch

import pytest
from hexbytes import HexBytes
from web3 import Web3
from web3.datastructures import AttributeDict

from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.util import setup_web3
from aquarius.myapp import app
from tests.ddos.ddo_event_sample_v4 import ddo_event_sample_v4
from tests.helpers import get_ddo, new_ddo, send_create_update_tx, test_account1

event_sample = AttributeDict(
    {
        "args": AttributeDict(
            {
                "dataToken": "0xe22570D8ea2D8004023A928FbEb36f14738C62c9",
                "createdBy": "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260",
                "flags": b"\x00",
                "data": "",
                "decryptorUrl": "http://localhost:8030",
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
                "decryptorUrl": "http://localhost:8030",
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
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None, None
    )
    processor.allowed_publishers = None
    assert processor.is_publisher_allowed(processor.sender_address) is True


def test_check_document_hash():
    original_dict = {"some_json": "for testing"}
    original_string = json.dumps(original_dict)
    hash_result = sha256(original_string.encode("utf-8")).hexdigest()
    event_sample.args.__dict__["metaDataHash"] = Web3.toBytes(hexstr=hash_result)

    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, None, None, None, None
    )
    assert processor.check_document_hash(original_dict) is True


def test_process_fallback(monkeypatch, client, base_ddo_url, events_object):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
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
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, web3, None, None, None, None, None
    )

    bk_block = processor.block
    processor.block = 0
    old_asset = {
        "event": {"blockNo": 100, "txid": "placeholder"},
        "publicKey": [{"owner": "some_address"}],
    }
    assert processor.check_update(None, old_asset, "") is False

    processor.block = bk_block
    assert processor.check_update(None, old_asset, "") is False

    address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    old_asset = {
        "event": {"blockNo": 100, "txid": "placeholder"},
        "publicKey": [{"owner": address}],
    }
    new_asset = old_asset
    assert processor.check_update(new_asset, old_asset, address) is False
