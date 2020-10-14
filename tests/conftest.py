#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import os

import pytest
from ocean_lib.config import Config
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.web3_provider import Web3Provider

from aquarius.events.events_monitor import EventsMonitor
from aquarius.constants import BaseURLs
from aquarius.events.util import get_artifacts_path
from aquarius.run import app

app = app

EVENTS_INSTANCE = None


@pytest.fixture
def base_ddo_url():
    return BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo'


@pytest.fixture
def client_with_no_data():
    client = app.test_client()
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo')
    yield client


@pytest.fixture
def client():
    client = app.test_client()

    yield client


@pytest.fixture
def events_object():
    global EVENTS_INSTANCE
    if not EVENTS_INSTANCE:
        config_file = os.getenv('CONFIG_FILE', 'config.ini')
        network_rpc = os.environ.get('EVENTS_RPC', 'http://127.0.0.1:8545')

        ConfigProvider.set_config(Config(config_file))
        from ocean_lib.ocean.util import get_web3_connection_provider

        Web3Provider.init_web3(provider=get_web3_connection_provider(network_rpc))
        ContractHandler.set_artifacts_path(get_artifacts_path())

        EVENTS_INSTANCE = EventsMonitor(
            Web3Provider.get_web3(),
            app.config['CONFIG_FILE']
        )
        EVENTS_INSTANCE.store_last_processed_block(0)
    return EVENTS_INSTANCE
