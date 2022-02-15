#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime
import pytest
from unittest.mock import Mock, patch

from aquarius.graphql import get_number_orders, get_last_block, get_transport


def test_get_number_orders():
    client = Mock()
    client.execute.return_value = {"tokens": [{"orderCount": 14}]}
    last_sync_block = 10
    with patch("aquarius.graphql.get_client") as client_mock:
        client_mock.return_value = client
        with patch("aquarius.graphql.get_last_block") as block_mock:
            block_mock.side_effect = [10, 11]
            assert get_number_orders("0x01", last_sync_block) == 14


def test_get_number_orders_exception():
    client = Mock()
    client.execute.side_effect = TypeError()
    last_sync_block = 10
    with patch("aquarius.graphql.get_client") as client_mock:
        client_mock.return_value = client
        with patch("aquarius.graphql.get_last_block") as block_mock:
            block_mock.return_value = 11
            assert get_number_orders("0x01", last_sync_block) == -1


def test_get_last_block():
    client = Mock()
    client.execute.return_value = {"_meta": {"block": {"number": 17}}}
    assert get_last_block(client) == 17

    client = Mock()
    client.execute.side_effect = KeyError()
    with pytest.raises(IndexError, match="Can not get last block name"):
        get_last_block(client)


def test_get_transport():
    with patch("aquarius.graphql.get_network_name") as mock:
        mock.return_value = "network"
        transport = get_transport()

    assert (
        transport.url
        == "http://subgraph.network.oceanprotocol.com/subgraphs/name/oceanprotocol/ocean-subgraph"
    )
