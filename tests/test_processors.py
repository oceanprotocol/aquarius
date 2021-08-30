import pytest
from hexbytes import HexBytes
from unittest.mock import patch
from web3.datastructures import AttributeDict

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.events.processors import MetadataCreatedProcessor
from aquarius.events.util import setup_web3
from aquarius.myapp import app


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


def test_check_permission(monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "http://rbac")
    processor = MetadataCreatedProcessor(
        event_sample, None, None, None, None, None, None
    )
    with patch("requests.post") as mock:
        mock.side_effect = Exception("Boom!")
        assert processor.check_permission("some_address") is False

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


def test_process(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    web3 = setup_web3(config_file)
    # mock es_instance
    processor = MetadataCreatedProcessor(
        event_sample, None, web3, None, None, None, None
    )
    processor.process()
