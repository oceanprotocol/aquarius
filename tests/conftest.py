#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import json

import pytest
from web3 import Web3
from pathlib import Path

from aquarius.events.events_monitor import EventsMonitor
from aquarius.constants import BaseURLs
from aquarius.events.http_provider import get_web3_connection_provider
from aquarius.run import app
from aquarius.ddo_checker import ddo_checker

app = app

EVENTS_INSTANCE = None


@pytest.fixture
def base_ddo_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/assets/ddo"


@pytest.fixture
def chains_url():
    return BaseURLs.BASE_AQUARIUS_URL + "/chains"


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

        EVENTS_INSTANCE = EventsMonitor(web3, app.config["AQUARIUS_CONFIG_FILE"])
        EVENTS_INSTANCE.store_last_processed_block(0)
    return EVENTS_INSTANCE


PATH_SAMPLES_DIR = Path().cwd() / "tests" / "metadata_samples"

PATH_SAMPLE_METADATA_LOCAL = PATH_SAMPLES_DIR / "sample_metadata_local.json"
assert PATH_SAMPLE_METADATA_LOCAL.exists(), "Path not found: {}".format(
    PATH_SAMPLE_METADATA_LOCAL
)

PATH_SAMPLE_METADATA_REMOTE = PATH_SAMPLES_DIR / "sample_metadata_remote.json"
assert PATH_SAMPLE_METADATA_REMOTE.exists(), "Path not found: {}".format(
    PATH_SAMPLE_METADATA_REMOTE
)

PATH_ALGORITHM_METADATA_LOCAL = PATH_SAMPLES_DIR / "algorithm_metadata_local.json"
PATH_ALGORITHM_METADATA_REMOTE = PATH_SAMPLES_DIR / "algorithm_metadata_remote.json"


def _load_sample_path(path, msg):
    this_json = {}
    try:
        with open(str(path)) as json_file:
            this_json = json.load(json_file)
    except TypeError as e:
        print(f"error: {e}")
    print(msg)
    return this_json


@pytest.fixture
def schema_local_dict():
    return _load_sample_path(
        ddo_checker.LOCAL_SCHEMA_FILE, f"Loaded schema: {ddo_checker.LOCAL_SCHEMA_FILE}"
    )


@pytest.fixture
def schema_remote_dict():
    return _load_sample_path(
        ddo_checker.REMOTE_SCHEMA_FILE,
        f"Loaded schema: {ddo_checker.REMOTE_SCHEMA_FILE}",
    )


@pytest.fixture
def sample_metadata_dict_local():
    return _load_sample_path(
        PATH_SAMPLE_METADATA_LOCAL, f"Loaded sample: {PATH_SAMPLE_METADATA_LOCAL}"
    )


@pytest.fixture
def sample_metadata_dict_remote():
    return _load_sample_path(
        PATH_SAMPLE_METADATA_REMOTE, f"Loaded sample: {PATH_SAMPLE_METADATA_REMOTE}"
    )


@pytest.fixture
def path_sample_metadata_local():
    return PATH_SAMPLE_METADATA_LOCAL


@pytest.fixture
def path_sample_metadata_remote():
    return PATH_SAMPLE_METADATA_REMOTE


@pytest.fixture
def sample_algorithm_md_dict_local():
    return _load_sample_path(
        PATH_ALGORITHM_METADATA_LOCAL, f"Loaded sample: {PATH_ALGORITHM_METADATA_LOCAL}"
    )


@pytest.fixture
def sample_algorithm_md_dict_remote():
    return _load_sample_path(
        PATH_ALGORITHM_METADATA_REMOTE,
        f"Loaded sample: {PATH_ALGORITHM_METADATA_REMOTE}",
    )
