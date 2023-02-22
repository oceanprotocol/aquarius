#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
from pathlib import Path

import pytest
from web3 import Web3

from aquarius.constants import BaseURLs
from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.run import app

app = app

EVENTS_INSTANCE = None


@pytest.fixture
def base_ddo_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/assets/ddo"


@pytest.fixture
def query_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/assets/query"


@pytest.fixture
def chains_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/chains"


@pytest.fixture
def validation_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/validation"


@pytest.fixture
def client_with_no_data():
    client = app.test_client()
    client.delete(BaseURLs.BASE_AQUARIUS_URL + "/assets/ddo")
    yield client


@pytest.fixture
def client():
    client = app.test_client()

    yield client


@pytest.fixture
def events_object():
    global EVENTS_INSTANCE
    if not EVENTS_INSTANCE:
        network_rpc = os.environ.get("EVENTS_RPC", "http://127.0.0.1:8545")
        provider = get_web3_connection_provider(network_rpc)
        web3 = Web3(provider)

        EVENTS_INSTANCE = EventsMonitor(web3)
        EVENTS_INSTANCE.store_last_processed_block(0)
    return EVENTS_INSTANCE
