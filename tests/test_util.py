#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from aquarius.app.auth_util import compare_eth_addresses
from aquarius.app.util import (
    check_no_urls_in_files,
    check_required_attributes,
    datetime_converter,
    get_bool_env_value,
    sanitize_record,
    validate_date_format,
)
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.events.util import get_network_name, setup_web3
from aquarius.log import setup_logging
from aquarius.myapp import app

logger = logging.getLogger(__name__)


def test_get_bool_env_value():
    name = "TEST_VAR"

    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 0) is False
    assert get_bool_env_value(name, 1) is True
    with pytest.raises(AssertionError):
        get_bool_env_value(name, "1")

    os.environ[name] = "0"
    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 1) is False
    assert get_bool_env_value(name, 0) is False
    os.environ[name] = "1"
    assert get_bool_env_value(name) is True
    assert get_bool_env_value(name, 0) is True
    assert get_bool_env_value(name, 1) is True
    os.environ[name] = "token"
    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 0) is False
    assert get_bool_env_value(name, 1) is True


class MetadataUpdaterTestClass(BlockProcessingClass):
    @property
    def block_envvar(self):
        return "METADATA_CONTRACT_BLOCK"

    def get_last_processed_block(self):
        return 100

    def store_last_processed_block(self, block):
        pass


def test_get_set_last_block_with_ignore(monkeypatch):
    monkeypatch.setenv("IGNORE_LAST_BLOCK", "1")
    monkeypatch.setenv("METADATA_CONTRACT_BLOCK", "20")

    mu = MetadataUpdaterTestClass()

    assert mu.get_or_set_last_block() == 20


def test_bad_chunk_size(monkeypatch):
    monkeypatch.setenv("BLOCKS_CHUNK_SIZE", "not an int")
    mu = MetadataUpdaterTestClass()
    mu.get_or_set_last_block()
    assert mu.blockchain_chunk_size == 1000


def test_get_set_last_block_without_ignore(monkeypatch):
    monkeypatch.setenv("IGNORE_LAST_BLOCK", "0")
    monkeypatch.setenv("METADATA_CONTRACT_BLOCK", "20")

    mu = MetadataUpdaterTestClass()

    assert mu.get_or_set_last_block() == 100


def test_compare_eth_addresses():
    address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    assert not compare_eth_addresses(address, "notAnAddress", logger)
    assert not compare_eth_addresses("notAnAddress", address, logger)
    assert compare_eth_addresses(address.upper(), address, logger)


def test_datetime_converter():
    assert datetime_converter(datetime.now())


def test_check_no_urls_in_files_fails():
    main = {"files": [{"url": "test"}]}
    message, code = check_no_urls_in_files(main, "GET")
    assert message == "GET request failed: url is not allowed in files "
    assert code == 400


def test_date_format_validator():
    date = "2000-10-31T01:30:00.000-05:00"
    assert validate_date_format(date) == (None, None)


def test_invalid_date():
    date = "XXXX"
    assert validate_date_format(date) == (
        "Incorrect data format, should be ISO Datetime Format",
        400,
    )


def test_sanitize_record():
    record = {"_id": "something", "other_value": "something else"}
    result = json.loads(sanitize_record(record))
    assert "_id" not in result
    assert result["other_value"] == "something else"


def test_check_required_attributes_errors():
    result, result_code = check_required_attributes("", {}, "method")
    assert result == "payload seems empty."
    assert result_code == 400

    result, result_code = check_required_attributes(
        ["key2", "key2"], {"key": "val"}, "method"
    )
    assert result == "\"{'key2'}\" are required in the call to method"
    assert result_code == 400


class BlockProcessingClassChild(BlockProcessingClass):
    def get_last_processed_block(self):
        raise Exception("BAD!")

    def store_last_processed_block(self, block):
        pass


def test_block_processing_class_no_envvar():
    bpc = BlockProcessingClassChild()
    assert bpc.block_envvar == ""
    assert bpc.get_or_set_last_block() == 0


def test_get_web3_connection_provider(monkeypatch):
    assert (
        get_web3_connection_provider("http://something").endpoint_uri
        == "http://something"
    )
    assert (
        get_web3_connection_provider("wss://something").endpoint_uri
        == "wss://something"
    )
    assert (
        get_web3_connection_provider("ganache").endpoint_uri == "http://127.0.0.1:8545"
    )
    assert (
        get_web3_connection_provider("polygon").endpoint_uri
        == "https://rpc.polygon.oceanprotocol.com"
    )
    with pytest.raises(AssertionError):
        get_web3_connection_provider("not_a_network")
    assert get_web3_connection_provider("kovan").endpoint_uri == "http://127.0.0.1:8545"
    monkeypatch.setenv("NETWORK_URL", "wss://kovan")
    assert get_web3_connection_provider("kovan").endpoint_uri == "wss://kovan"


def test_get_network_name(monkeypatch):
    monkeypatch.delenv("NETWORK_NAME")
    monkeypatch.setenv("EVENTS_RPC", "wss://something.com")
    assert get_network_name() == "something"

    monkeypatch.setenv("EVENTS_RPC", "http://something-else.com")
    assert get_network_name() == "something-else"

    monkeypatch.setenv("EVENTS_RPC", "https://something-else-entirely.com")
    assert get_network_name() == "something-else-entirely"

    monkeypatch.setenv("EVENTS_RPC", "other")
    assert get_network_name() == "other"

    monkeypatch.setenv("EVENTS_RPC", "")
    with pytest.raises(AssertionError):
        get_network_name()


def test_setup_web3(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monkeypatch.setenv("NETWORK_NAME", "rinkeby")
    assert setup_web3(config_file, logger)


def test_setup_logging(monkeypatch):
    with patch("logging.config.dictConfig") as mock:
        mock.side_effect = Exception("Boom!")
        setup_logging()

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    setup_logging()

    setup_logging("some_madeup_path")
