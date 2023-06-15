#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from eth_account import Account
import json
import logging
import os
from requests.models import Response
from datetime import datetime
from unittest.mock import patch, Mock

import pytest

from aquarius.app.auth_util import compare_eth_addresses
from aquarius.app.util import (
    datetime_converter,
    get_bool_env_value,
    sanitize_record,
    sanitize_query_result,
    get_aquarius_wallet,
    AquariusPrivateKeyException,
    get_signature_vrs,
)
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.events.util import (
    get_network_name,
    setup_web3,
    deploy_datatoken,
    get_metadata_start_block,
)
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


def test_sanitize_record():
    record = {"_id": "something", "other_value": "something else"}
    result = json.loads(sanitize_record(record))
    assert "_id" not in result
    assert result["other_value"] == "something else"


def test_sanitize_record_through_rbac(monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "test")

    with patch("requests.post") as mock:
        response = Mock(spec=Response)
        response.json.return_value = {"this_is": "SPARTAAA!"}
        response.status_code = 200
        mock.return_value = response

        result = json.loads(sanitize_record({}))
        assert result["this_is"] == "SPARTAAA!"

    with patch("requests.post") as mock:
        response = Mock(spec=Response)
        response.status_code = 404
        mock.return_value = response

        result = json.loads(sanitize_record({"this_is": "something else"}))
        assert result["this_is"] == "something else"


def test_sanitize_query_result(monkeypatch):
    result = sanitize_query_result({"this_is": "Athens, for some reason."})
    assert result["this_is"] == "Athens, for some reason."

    monkeypatch.setenv("RBAC_SERVER_URL", "test")

    with patch("requests.post") as mock:
        response = Mock(spec=Response)
        response.json.return_value = {"this_is": "SPARTAAA!"}
        response.status_code = 200
        mock.return_value = response

        result = sanitize_query_result({})
        assert result["this_is"] == "SPARTAAA!"

    with patch("requests.post") as mock:
        response = Mock(spec=Response)
        response.status_code = 404
        mock.return_value = response

        result = sanitize_query_result({"this_is": "something else"})
        assert result["this_is"] == "something else"


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
    monkeypatch.setenv("NETWORK_NAME", "rinkeby")
    assert setup_web3(logger)


def test_config_rpc(monkeypatch):
    monkeypatch.setenv("PUBLIC_RPC", "https://rpc-mumbai.maticvigil.com/")

    with pytest.raises(
        Exception, match="Mismatch of chain IDs between configuration and events RPC!"
    ):
        setup_web3(logger)


def test_setup_logging(monkeypatch):
    with patch("logging.config.dictConfig") as mock:
        mock.side_effect = Exception("Boom!")
        setup_logging()

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    setup_logging()

    setup_logging("some_madeup_path")


def test_wallet_missing(monkeypatch):
    monkeypatch.delenv("PRIVATE_KEY")
    with pytest.raises(AquariusPrivateKeyException):
        get_aquarius_wallet()

    assert get_signature_vrs("".encode("utf-8")) == {
        "hash": "",
        "publicKey": "",
        "r": "",
        "s": "",
        "v": "",
    }


def test_deploy_datatoken_fails():
    web3 = setup_web3()
    test_account1 = Account.from_key(os.environ.get("EVENTS_TESTS_PRIVATE_KEY", None))
    with patch.object(type(web3.eth), "get_transaction_receipt") as mock:
        mock.side_effect = Exception()
        with pytest.raises(Exception, match="tx not found"):
            deploy_datatoken(web3, test_account1, "TT1", "TT1Symbol")
