#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
from pathlib import Path
import pkg_resources
from pyshacl import validate
import pytest
import rdflib

from aquarius.ddo_checker.shacl_checker import validate_dict, parse_report_to_errors
from tests.ddos.ddo_sample1_v4 import json_dict
from tests.ddos.ddo_sample_algorithm_v4 import algorithm_ddo_sample


def test_sample_schema():
    path = "sample_schemas/remote_v4.ttl"
    schema_file = Path(pkg_resources.resource_filename("tests", path)).read_text()

    data = json.dumps(
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@type": "DDO",
            "id": "123",
            "version": "4.0.0",
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
            "version": "4.0.0",
        }
    )

    dataGraph = rdflib.Graph().parse(data=data, format="json-ld")

    conforms, results_graph, _ = validate(dataGraph, shacl_graph=schema_file)
    assert not conforms
    errors = parse_report_to_errors(results_graph)
    assert "id" in errors
    assert errors["id"] == "Less than 1 value on schema:id"

    data = json.dumps(
        {
            "@context": {"@vocab": "http://schema.org/"},
            "@type": "DDO",
            "id": "did:op:123",
            "version": "4.0.0",
        }
    )

    dataGraph = rdflib.Graph().parse(data=data, format="json-ld")

    conforms, results_graph, results_text = validate(dataGraph, shacl_graph=schema_file)
    assert conforms
    errors = parse_report_to_errors(results_graph)
    assert not errors


def test_remote_ddo_passes():
    valid, _ = validate_dict(json_dict)
    assert valid

    valid, errors = validate_dict(algorithm_ddo_sample)
    assert valid


def test_remote_ddo_fails():
    for required_prop in ["id", "version"]:
        _copy = copy.deepcopy(json_dict)
        _copy.pop(required_prop)

        valid, errors = validate_dict(_copy)
        assert not valid
        assert required_prop in errors

    _copy = copy.deepcopy(json_dict)
    _copy["version"] = "something not semver"

    with pytest.raises(AssertionError):
        validate_dict(_copy)

    # services invalid
    _copy = copy.deepcopy(json_dict)
    _copy["services"][0].pop("files")
    valid, errors = validate_dict(_copy)
    assert not valid
    assert "services" in errors

    for required_prop in ["type", "datatokenAddress", "serviceEndpoint", "timeout"]:
        _copy = copy.deepcopy(json_dict)
        _copy["services"][0].pop(required_prop)

        valid, errors = validate_dict(_copy)
        assert not valid
        assert "services" in errors

    _copy = copy.deepcopy(json_dict)
    _copy["services"][0]["timeout"] = "not an integer"

    valid, errors = validate_dict(_copy)
    assert not valid
    assert "services" in errors


def test_remote_ddo_metadata_fails():
    for required_prop in ["description", "name", "type", "author", "license"]:
        _copy = copy.deepcopy(json_dict)
        _copy["metadata"].pop(required_prop)

        valid, _ = validate_dict(_copy)
        assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["links"] = 14  # not a link or string list
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(json_dict)
    _copy["metadata"]["tags"] = 14  # not a string or string list
    valid, _ = validate_dict(_copy)
    assert not valid

    _copy = copy.deepcopy(algorithm_ddo_sample)
    _copy["metadata"]["algorithm"]["container"] = None

    valid, errors = validate_dict(_copy)
    assert not valid
