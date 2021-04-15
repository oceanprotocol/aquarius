#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import logging
import pytest
from datetime import datetime

from aquarius.app.util import (
    get_bool_env_value,
    datetime_converter,
    check_no_urls_in_files,
)
from aquarius.app.auth_util import compare_eth_addresses
from aquarius.block_utils import BlockProcessingClass

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
