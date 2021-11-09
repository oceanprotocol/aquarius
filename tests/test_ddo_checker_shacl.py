#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from pathlib import Path
import pkg_resources
from pyshacl import validate
import rdflib

from aquarius.ddo_checker.ddo_checker_shacl import parse_report_to_errors


def test_basic():
    path = "ddo_checker/shacl_schemas/v4/remote_v4.ttl"
    schema_file = Path(pkg_resources.resource_filename("aquarius", path)).read_text()

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
