#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

# from metadata_validator.json_versions import json4, json1
# from metadata_validator.schema_definitions import valid_schema
import copy
import pytest

from aquarius.ddo_checker.ddo_checker import validate_dict
from tests.ddos.ddo_sample1_v4 import json_dict
from tests.ddos.ddo_sample_algorithm_v4 import algorithm_ddo_sample


def test_remote_metadata_passes():
    valid, _ = validate_dict(json_dict)
    assert valid

    valid, _ = validate_dict(algorithm_ddo_sample)
    assert valid


def test_remote_ddo_fails():
    for required_prop in ["id", "created", "updated", "version"]:
        _copy = copy.deepcopy(json_dict)
        _copy.pop(required_prop)

        valid, _ = validate_dict(_copy)
        assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["version"] = "something not semver"

    with pytest.raises(AssertionError):
        validate_dict(_copy)

    # status invalid
    _copy = copy.deepcopy(json_dict)
    _copy["status"] = {"additionalProp": "something"}
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["status"] = {"isListed": "something not boolean"}
    valid, _ = validate_dict(_copy)
    assert not valid

    # services invalid
    _copy = copy.deepcopy(json_dict)
    _copy["services"][0]["files"].pop("encryptedFiles")
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["services"][0]["files"]["files"][0]["contentType"] = None
    valid, _ = validate_dict(_copy)
    assert not valid

    for required_prop in ["type", "datatokenAddress", "providerEndpoint", "timeout"]:
        _copy = copy.deepcopy(json_dict)
        _copy["services"][0].pop(required_prop)

        valid, _ = validate_dict(_copy)
        assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["services"][0]["timeout"] = "not an integer"

    valid, _ = validate_dict(_copy)
    assert not valid


def test_remote_ddo_metadata_fails():
    for required_prop in ["description", "name", "type", "author", "license"]:
        _copy = copy.deepcopy(json_dict)
        _copy["metadata"].pop(required_prop)

        valid, _ = validate_dict(_copy)
        assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["links"] = {"url_is_missing": "in this dict"}
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["tags"] = "malformed if not an object"
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(algorithm_ddo_sample)
    _copy["metadata"]["algorithm"]["container"] = None

    valid, errors = validate_dict(_copy)
    assert not valid
