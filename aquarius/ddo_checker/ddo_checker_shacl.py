#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import rdflib


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
