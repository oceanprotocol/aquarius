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

from aquarius.ddo_checker.ddo_checker_shacl import validate_dict, parse_report_to_errors
from tests.ddos.ddo_sample1_v4 import json_dict


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


def test_remote_ddo_fails():
    # structure from test_ddo_checker_v4
    for required_prop in ["id", "created", "updated", "version"]:
        _copy = copy.deepcopy(json_dict)
        _copy.pop(required_prop)

        valid, errors = validate_dict(_copy)
        assert not valid
        assert required_prop in errors

    _copy = copy.deepcopy(json_dict)
    _copy["version"] = "something not semver"

    with pytest.raises(AssertionError):
        validate_dict(_copy)

    # TODO: not yet implemented, need to add more to shacl schema
    # TODO: metadata validation
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
