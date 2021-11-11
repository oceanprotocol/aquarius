#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
import rdflib
from pathlib import Path
import pkg_resources
from pyshacl import validate


def get_schema(version="v4.0.0"):
    path = "ddo_checker/shacl_schemas/v4/remote_" + version + ".ttl"

    schema_file = Path(pkg_resources.resource_filename("aquarius", path))
    assert schema_file.exists(), "Can't find schema file {}".format(schema_file)

    return schema_file.read_text()


def parse_report_to_errors(results_graph):
    paths = [
        str(x[2]).replace("http://schema.org/", "")
        for x in results_graph.triples(
            (None, rdflib.term.URIRef("http://www.w3.org/ns/shacl#resultPath"), None)
        )
    ]
    messages = [
        beautify_message(str(x[2]))
        for x in results_graph.triples(
            (None, rdflib.term.URIRef("http://www.w3.org/ns/shacl#resultMessage"), None)
        )
    ]

    return dict(zip(paths, messages))


def beautify_message(message):
    if message.startswith("Less than 1 values on"):
        index = message.find("->") + 2
        message = "Less than 1 value on " + message[index:]

    return message


def validate_dict(dict_orig):
    dictionary = copy.deepcopy(dict_orig)
    dictionary["@type"] = "DDO"

    if "@context" not in dict_orig or not isinstance(dict_orig["@context"], (list, dict)):
        return False, {"@context": "Context is missing or invalid."}

    # @context key is reserved in JSON-LD format
    dictionary["@context"] = {"@vocab": "http://schema.org/"}
    dictionary_as_string = json.dumps(dictionary)

    version = dictionary.get("version", "v4.0.0")
    schema_file = get_schema(version)
    dataGraph = rdflib.Graph().parse(data=dictionary_as_string, format="json-ld")

    conforms, results_graph, _ = validate(dataGraph, shacl_graph=schema_file)
    errors = parse_report_to_errors(results_graph)

    return conforms, errors
