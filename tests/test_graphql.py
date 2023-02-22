#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime
import json
import pytest
from unittest.mock import Mock, patch

from aquarius.graphql import get_number_orders_price, get_last_block, get_transport


def test_get_number_orders():
    client = Mock()
    client.execute.return_value = {
        "tokens": [{"fixedRateExchanges": [{"price": "20.5"}], "orderCount": "14"}]
    }
    last_sync_block = 10
    with patch("aquarius.graphql.get_client") as client_mock:
        client_mock.return_value = client
        with patch("aquarius.graphql.get_last_block") as block_mock:
            block_mock.side_effect = [10, 11]
            assert get_number_orders_price("0x01", last_sync_block, 8996) == (
                14,
                {"value": 20.5},
            )


def test_get_number_orders_exception():
    client = Mock()
    client.execute.side_effect = TypeError()
    last_sync_block = 10
    with patch("aquarius.graphql.get_client") as client_mock:
        client_mock.return_value = client
        with patch("aquarius.graphql.get_last_block") as block_mock:
            block_mock.return_value = 11
            assert get_number_orders_price("0x01", last_sync_block, 8996) == (-1, {})


def test_get_last_block():
    client = Mock()
    client.execute.return_value = {"_meta": {"block": {"number": 17}}}
    assert get_last_block(client) == 17

    client = Mock()
    client.execute.side_effect = KeyError()
    with pytest.raises(IndexError, match="Can not get last block name"):
        get_last_block(client)


def test_get_transport(monkeypatch):
    monkeypatch.setenv(
        "SUBGRAPH_URLS",
        json.dumps({"4": "http://v4.subgraph.network.oceanprotocol.com"}),
    )
    transport = get_transport(4)

    assert (
        transport.url
        == "http://v4.subgraph.network.oceanprotocol.com/subgraphs/name/oceanprotocol/ocean-subgraph"
    )

    with pytest.raises(Exception, match="Subgraph not defined for this chain."):
        transport = get_transport(5)
