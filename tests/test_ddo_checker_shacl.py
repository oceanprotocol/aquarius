#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
import logging
from pathlib import Path
import pkg_resources

from pyshacl import validate
import pytest
import rdflib

from aquarius.ddo_checker.shacl_checker import (
    validate_dict,
    parse_report_to_errors,
    CURRENT_VERSION,
)
from tests.ddos.ddo_sample1_v4 import json_dict
from tests.ddos.ddo_sample_algorithm_v4 import algorithm_ddo_sample

logger = logging.getLogger("aquarius")


def test_sample_schema():
    path = "sample_schemas/remote_v4.ttl"
    schema_file = Path(pkg_resources.resource_filename("tests", path)).read_text()

    data = json.dumps(
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@type": "DDO",
            "id": "123",
            "version": CURRENT_VERSION,
        }
    )

    dataGraph = rdflib.Graph().parse(data=data, format="json-ld")

    conforms, results_graph, _ = validate(dataGraph, shacl_graph=schema_file)
    assert not conforms
    errors = parse_report_to_errors(results_graph)
    assert "id" in errors
    assert errors["id"] == "Value does not match pattern '^did\:op\:(.*)$'"

    data = json.dumps(
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@type": "DDO",
            "version": CURRENT_VERSION,
        }
    )

    dataGraph = rdflib.Graph().parse(data=data, format="json-ld")

    conforms, results_graph, _ = validate(dataGraph, shacl_graph=schema_file)
    assert not conforms
    errors = parse_report_to_errors(results_graph)
    assert "id" in errors
    assert "Less than 1 value on schema" in errors["id"]

    data = json.dumps(
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@type": "DDO",
            "id": "did:op:123",
            "version": CURRENT_VERSION,
        }
    )

    dataGraph = rdflib.Graph().parse(data=data, format="json-ld")

    conforms, results_graph, results_text = validate(dataGraph, shacl_graph=schema_file)
    assert conforms
    errors = parse_report_to_errors(results_graph)
    assert not errors


def test_remote_ddo_passes():
    valid, _ = validate_dict(json_dict, json_dict["chainId"], json_dict["nftAddress"])
    assert valid

    valid, _ = validate_dict(
        algorithm_ddo_sample,
        algorithm_ddo_sample["chainId"],
        algorithm_ddo_sample["nftAddress"],
    )
    assert valid


def test_remote_ddo_fails():
    _copy = copy.deepcopy(json_dict)
    _copy.pop("@context")
    valid, errors = validate_dict(_copy, "", "")
    assert not valid
    assert errors["@context"] == "Context is missing or invalid."

    _copy = copy.deepcopy(json_dict)
    valid, errors = validate_dict(_copy, "", "")
    assert not valid
    assert errors["chainId"] == "chainId is missing or invalid."
    assert errors["nftAddress"] == "nftAddress is missing or invalid."

    _copy = copy.deepcopy(json_dict)
    valid, errors = validate_dict(_copy, 1234, json_dict["nftAddress"])
    assert not valid
    assert errors["id"] == "did is not valid for chain Id and nft address"

    _copy = copy.deepcopy(json_dict)
    valid, errors = validate_dict(_copy, json_dict["chainId"], "0xabcd")
    assert not valid
    assert errors["id"] == "did is not valid for chain Id and nft address"

    for required_prop in ["id", "version"]:
        _copy = copy.deepcopy(json_dict)
        _copy.pop(required_prop)

        valid, errors = validate_dict(
            _copy, json_dict["chainId"], json_dict["nftAddress"]
        )
        assert not valid
        assert required_prop in errors

    _copy = copy.deepcopy(json_dict)
    _copy["version"] = "something not semver"

    with pytest.raises(AssertionError):
        validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])

    # services invalid
    _copy = copy.deepcopy(json_dict)
    _copy["services"][0].pop("files")
    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid
    assert "services" in errors

    for required_prop in ["type", "datatokenAddress", "serviceEndpoint", "timeout"]:
        _copy = copy.deepcopy(json_dict)
        _copy["services"][0].pop(required_prop)

        valid, errors = validate_dict(
            _copy, json_dict["chainId"], json_dict["nftAddress"]
        )
        assert not valid
        assert "services" in errors

    _copy = copy.deepcopy(json_dict)
    _copy["services"][0]["timeout"] = "not an integer"

    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid
    assert "services" in errors


def test_remote_ddo_failures_limits():
    # simple maxLength check (metadata name)
    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["name"] = "a" * 513
    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid
    assert "metadata" in errors

    # too many tags
    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["tags"] = [str(x) for x in range(0, 65)]
    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid
    assert "metadata" in errors

    # algorithm container checksum is the wrong length
    _copy = copy.deepcopy(algorithm_ddo_sample)
    _copy["metadata"]["algorithm"]["container"]["checksum"] = ("sha2:",)
    valid, errors = validate_dict(
        _copy,
        algorithm_ddo_sample["chainId"],
        algorithm_ddo_sample["nftAddress"],
    )
    assert not valid
    assert "metadata" in errors


def test_remote_ddo_metadata_fails():
    for required_prop in ["description", "name", "type", "author", "license"]:
        _copy = copy.deepcopy(json_dict)
        _copy["metadata"].pop(required_prop)

        valid, _ = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
        assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["created"] = "not iso format"
    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid
    assert errors["metadata"] == "created is not in iso format."

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["links"] = 14  # not a link or string list
    valid, _ = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["tags"] = 14  # not a string or string list
    valid, _ = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid

    _copy = copy.deepcopy(algorithm_ddo_sample)
    _copy["metadata"]["algorithm"]["container"] = None

    valid, errors = validate_dict(_copy, json_dict["chainId"], json_dict["nftAddress"])
    assert not valid


def test_remote_ddo_without_service():
    _copy = copy.deepcopy(json_dict)
    _ = _copy.pop("services")
    assert not _copy.get("services")
    assert _copy["version"] == CURRENT_VERSION
    valid, _ = validate_dict(
        _copy,
        _copy["chainId"],
        _copy["nftAddress"],
    )
    assert valid
