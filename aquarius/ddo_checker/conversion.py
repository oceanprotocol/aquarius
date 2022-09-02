import json
import rdflib


def graph_to_dict(g):
    """
    Pass in a rdflib.Graph and get back a chunk of JSON using
    the Talis JSON serialization for RDF:
    http://n2.talis.com/wiki/RDF_JSON_Specification
    """
    result = json.loads(g.serialize(format="json-ld"))

    i = 0
    while i < len(result):
        if "http://www.w3.org/ns/shacl#property" in result[i]:
            sub_ids = [
                res["@id"] for res in result[i]["http://www.w3.org/ns/shacl#property"]
            ]

            del result[i]["http://www.w3.org/ns/shacl#property"]
            result[i]["properties"] = {}
            result[i]["nodes"] = {}
            for sub_id in sub_ids:
                ind, res = [
                    (ind, res)
                    for ind, res in enumerate(result)
                    if res.get("@id") == sub_id
                ][0]

                res.pop("@id")

                path = res.pop("http://www.w3.org/ns/shacl#path")
                path = path[0]["@id"].replace("http://schema.org/", "")

                values = {
                    k.replace("http://www.w3.org/ns/shacl#", ""): v[0].get("@value")
                    for k, v in res.items()
                    if v[0].get("@value")
                }
                result[i]["properties"][path] = values

                if not "http://www.w3.org/ns/shacl#node" in result[ind]:
                    del result[ind]
                else:
                    result[i]["nodes"][path] = result[ind][
                        "http://www.w3.org/ns/shacl#node"
                    ][0]["@id"]

        i += 1

    i = 0
    while i < len(result):
        if "nodes" not in result[i]:
            i += 1
            continue

        nodes = result[i]["nodes"]
        for node_key, node in nodes.items():
            result[i]["properties"][node_key] = [
                res["properties"] for res in result if res.get("@id") == node
            ][0]

        del result[i]["nodes"]
        i += 1

    return [res for res in result if res.get("@id") == "http://schema.org/DDOShape"][0][
        "properties"
    ]
