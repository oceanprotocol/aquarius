#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from pathlib import Path

import pytest

import plecos

# Select the latest schema path here
# PATH_SCHEMA_DIR = Path().cwd() / 'plecos' / 'schemas'
# print(PATH_SCHEMA_DIR)
# PATH_LATEST_SCHEMA = PATH_SCHEMA_DIR / 'metadata_190218.json'
# assert PATH_LATEST_SCHEMA.exists(), "Path not found: {}".format(PATH_LATEST_SCHEMA)

# Local sample

PATH_SAMPLES_DIR = Path().cwd() / "plecos" / "samples"
PATH_SAMPLE_METADATA_LOCAL = PATH_SAMPLES_DIR / "sample_metadata_local.json"
assert PATH_SAMPLE_METADATA_LOCAL.exists(), "Path not found: {}".format(
    PATH_SAMPLE_METADATA_LOCAL
)

PATH_ALGORITHM_METADATA_LOCAL = PATH_SAMPLES_DIR / "algorithm_metadata_local.json"
PATH_ALGORITHM_METADATA_REMOTE = PATH_SAMPLES_DIR / "algorithm_metadata_remote.json"

# Remote sample
PATH_SAMPLES_DIR = Path().cwd() / "plecos" / "samples"
PATH_SAMPLE_METADATA_REMOTE = PATH_SAMPLES_DIR / "sample_metadata_remote.json"
assert PATH_SAMPLE_METADATA_REMOTE.exists(), "Path not found: {}".format(
    PATH_SAMPLE_METADATA_REMOTE
)


def _load_sample_path(path, msg):
    this_json = {}
    try:
        with open(str(path)) as json_file:
            this_json = json.load(json_file)
    except TypeError as e:
        print(f"errpr: {e}")
    print(msg)
    return this_json


@pytest.fixture
def schema_local_dict():
    return _load_sample_path(
        plecos.LOCAL_SCHEMA_FILE, f"Loaded schema: {plecos.LOCAL_SCHEMA_FILE}"
    )


@pytest.fixture
def schema_remote_dict():
    return _load_sample_path(
        plecos.REMOTE_SCHEMA_FILE, f"Loaded schema: {plecos.REMOTE_SCHEMA_FILE}"
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
