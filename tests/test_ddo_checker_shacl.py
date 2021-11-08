#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from pathlib import Path
import pkg_resources
from pyshacl import validate
import rdflib


def test_basic():
    path = "ddo_checker/shacl_schemas/v4/remote_v4.ttl"
    schema_file = Path(pkg_resources.resource_filename("aquarius", path)).read_text()

    data = json.dumps({
        "@context": {"@vocab": "http://schema.org/"},
        "@type": "DDO",
        "id": "123"
    })

    dataGraph = rdflib.Graph().parse(data=data, format='json-ld')

    conforms, results_graph, results_text = validate(dataGraph, shacl_graph=schema_file)
    assert not conforms

    data = json.dumps({
        "@context": {"@vocab": "http://schema.org/"},
        "@type": "DDO",
    })

    dataGraph = rdflib.Graph().parse(data=data, format='json-ld')

    conforms, results_graph, results_text = validate(dataGraph, shacl_graph=schema_file)
    assert not conforms

    data = json.dumps({
        "@context": {"@vocab": "http://schema.org/"},
        "@type": "DDO",
        "id": "did:op:123"
    })

    dataGraph = rdflib.Graph().parse(data=data, format='json-ld')

    conforms, results_graph, results_text = validate(dataGraph, shacl_graph=schema_file)
    assert conforms
