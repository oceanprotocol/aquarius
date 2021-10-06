import pytest
from hexbytes import HexBytes
from unittest.mock import patch, Mock
from web3.datastructures import AttributeDict

from aquarius.events.decryptor import Decryptor
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
    OrderStartedProcessor
)
from aquarius.events.util import setup_web3
from aquarius.myapp import app

from tests.helpers import new_ddo, test_account1


event_sample = AttributeDict(
    {
        "args": AttributeDict(
            {
                "dataToken": "0xe22570D8ea2D8004023A928FbEb36f14738C62c9",
                "createdBy": "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260",
                "flags": b"\x00",
                "data": "",
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

order_started_sample = AttributeDict(
    {
        'address': '0x5C53218593244B7603b2F1dD47A2Fb9367552878',
        'blockHash': HexBytes('0xb399348447727a0912e8e67e04e69e9b62ad6f3b615abcb473a5a88505432f3b'),
        'blockNumber': 11139493,
        'data': '0x0000000000000000000000000000000000000000000000000de0b6b3a76400000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000005f983f000000000000000000000000000000000000000000000000000000000000000000',
        'logIndex': 164,
        'removed': False,
        'transactionHash': HexBytes('0x2732a08eb120e4d7e9227ab6b486ee319b20a323bd1bcb346cfd2aee9b9393f7'),
        'transactionIndex': 77
    }
)


def test_check_permission(monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "http://rbac")
    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, None, None, None
    )
    with patch("requests.post") as mock:
        mock.side_effect = Exception("Boom!")
        assert processor.check_permission("some_address") is False

    # will affect the process() function too
    decryptor = Mock(spec=Decryptor)
    decryptor.decode_ddo.return_value = "not none"
    processor.decryptor = decryptor
    with pytest.raises(Exception):
        with patch("requests.post") as mock:
            mock.side_effect = Exception("Boom!")
            processor.process()

    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, None, None, None, None, None
    )
    processor.decryptor = decryptor
    # will affect the process() function too
    with pytest.raises(Exception):
        with patch("requests.post") as mock:
            mock.side_effect = Exception("Boom!")
            processor.process()


def test_is_publisher_allowed():
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None
    )
    processor.allowed_publishers = None
    assert processor.is_publisher_allowed(processor.sender_address) is True


def test_make_record(sample_metadata_dict_remote):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None
    )
    sample_metadata_dict_remote["main"]["EXTRA ATTRIB!"] = 0
    assert processor.make_record(sample_metadata_dict_remote) is False

    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, web3, None, None, None, None
    )
    sample_metadata_dict_remote["main"]["EXTRA ATTRIB!"] = 0
    assert (
        processor.make_record(sample_metadata_dict_remote, {"created": "test"}) is False
    )


def test_process(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None
    )
    processor.process()

    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, web3, None, None, None, None
    )
    # falls back on the MetadataCreatedProcessor
    # since no es instance means read will throw an Exception
    with patch("aquarius.events.processors.MetadataCreatedProcessor.process") as mock:
        processor.process()
        mock.assert_called_once()


def test_do_decode_update():
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    processor = MetadataUpdatedProcessor(
        event_updated_sample, None, web3, None, None, None, None
    )

    bk_block = processor.block
    processor.block = 0
    asset = {
        "event": {"blockNo": 100, "txid": "placeholder"},
        "publicKey": [{"owner": "some_address"}],
    }
    assert processor.do_decode_update(asset, "") is False

    processor.block = bk_block
    assert processor.do_decode_update(asset, "") is False

    address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    asset = {
        "event": {"blockNo": 100, "txid": "placeholder"},
        "publicKey": [{"owner": address}],
    }
    assert processor.do_decode_update(asset, address) is False


def test_order_started_processor(sample_metadata_dict_remote):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    ddo = new_ddo(test_account1, web3, "test")
    import pdb; pdb.set_trace()
    processor = OrderStartedProcessor(
        ddo.did, es_instance, token_address, last_sync_block
    )

    updated_asset = processor.make_record(sample_metadata_dict_remote)
    assert updated_asset["numOrders"] == 2
