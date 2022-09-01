import rdflib


def graph_to_dict(g):
    """
    Pass in a rdflib.Graph and get back a chunk of JSON using
    the Talis JSON serialization for RDF:
    http://n2.talis.com/wiki/RDF_JSON_Specification
    """
    result = {}

    # go through all the triples in the graph
    for s, p, o in g:
        # initialize property dictionary if we've got a new subject
        if not str(s) in result:
            result[str(s)] = {}

        # initialize object list if we've got a new subject-property combo
        if not str(p) in result[str(s)]:
            result[str(s)][str(p)] = []

        # determine the value dictionary for the object
        v = {"value": str(o)}

        if isinstance(o, rdflib.term.URIRef):
            v["type"] = "uri"
        elif isinstance(o, rdflib.term.BNode):
            v["type"] = "bnode"
        elif isinstance(o, rdflib.term.Literal):
            v["type"] = "literal"
            if o.language:
                v["lang"] = o.language
            if o.datatype:
                v["datatype"] = str(o.datatype)

        # add the triple
        result[str(s)][str(p)].append(v)

    result.pop("http://schema.org/DDOShape")

    final_result = {}

    for key, result_item in result.items():
        fin_key = result_item["http://www.w3.org/ns/shacl#path"][0]["value"].replace(
            "http://schema.org/", ""
        )

        final_result[fin_key] = {}
        for kn, rin in result_item.items():
            if kn != "http://www.w3.org/ns/shacl#path":
                final_result[fin_key][
                    kn.replace("http://www.w3.org/ns/shacl#", "")
                ] = rin[0]["value"].replace("http://www.w3.org/2001/XMLSchema#", "")

    return final_result
