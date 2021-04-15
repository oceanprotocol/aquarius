#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import json
import logging
import pytest

from aquarius.app.util import get_bool_env_value
from aquarius.app.auth_util import compare_eth_addresses, has_update_request_permission
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


def test_has_update_request_permission(monkeypatch):
    monkeypatch.setenv("AQUA_VIP_ACCOUNTS", "badjson")
    assert has_update_request_permission("") is False

    address = "0xe2DD09d719Da89e5a3D0F2549c7E24566e947260"
    monkeypatch.setenv("AQUA_VIP_ACCOUNTS", json.dumps([address]))
    assert has_update_request_permission(address)


# TODO: add test for get_signer_address after clarification of the pending functions
