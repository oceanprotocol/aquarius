#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import patch

import elasticsearch

from aquarius.constants import BaseURLs
from aquarius.run import get_status
from tests.helpers import (
    run_request,
    run_request_get_data,
    send_create_update_tx,
    test_account1,
)


def test_get_ddo_exception(client, base_ddo_url):
    with patch("aquarius.app.es_instance.ElasticsearchInstance.get") as mock:
        mock.side_effect = Exception("Boom!")
        rv = client.get(base_ddo_url + "/1", content_type="application/json")
        assert rv.status_code == 404
        assert (
            rv.json["error"]
            == "Error encountered while searching the asset DID 1: Boom!."
        )


def test_get_metadata_exception(client):
    with patch("aquarius.app.es_instance.ElasticsearchInstance.get") as mock:
        mock.side_effect = Exception("Boom!")
        rv = client.get(
            "api/aquarius/assets/metadata/1", content_type="application/json"
        )
        assert rv.status_code == 404
        assert rv.json["error"] == "Error encountered while retrieving metadata: Boom!."


def test_get_assets_names_exception(client):
    with patch("aquarius.app.es_instance.ElasticsearchInstance.get") as mock:
        mock.side_effect = Exception("Boom!")
        base_url = BaseURLs.BASE_AQUARIUS_URL + "/assets"
        rv = run_request(client.post, base_url + "/names", {"didList": [1]})
        # just skips the name
        assert rv.status_code == 200


def test_transport_error(client, query_url):
    with patch("elasticsearch.Elasticsearch.search") as mock:
        ex = elasticsearch.exceptions.TransportError("test_error")
        mock.side_effect = ex
        rv = run_request(client.post, query_url, {"didList": [1]})
        assert rv.status_code == 400
        assert rv.json["error"] == "test_error"

    with patch("elasticsearch.Elasticsearch.search") as mock:
        mock.side_effect = Exception("Boom!")
        rv = run_request(client.post, query_url, {"didList": [1]})
        assert rv.status_code == 500
        assert rv.json["error"] == "Encountered Elasticsearch Exception: Boom!"


def test_chains_list_exceptions(client, chains_url):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = elasticsearch.exceptions.NotFoundError(
            "Boom!", meta={}, body={}
        )
        rv = client.get(chains_url + "/list", content_type="application/json")
        assert rv.status_code == 404
        assert rv.json["error"] == "No chains found."

    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = Exception("Boom!")
        rv = client.get(chains_url + "/list", content_type="application/json")
        assert rv.status_code == 404
        assert rv.json["error"] == "Error retrieving chains: Boom!."


def test_chains_status_exceptions(client, chains_url):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = elasticsearch.exceptions.NotFoundError(
            "Boom!", meta={}, body={}
        )
        rv = client.get(chains_url + "/status/1", content_type="application/json")
        assert rv.status_code == 404
        assert rv.json["error"] == "Chain 1 is not indexed."

    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = Exception("Boom!")
        rv = client.get(chains_url + "/status/1", content_type="application/json")
        assert rv.status_code == 404
        assert rv.json["error"] == "Error retrieving chain 1: Boom!."


def test_get_status():
    with patch("elasticsearch.Elasticsearch.ping") as mock:
        mock.return_value = False
        message, result = get_status()
        assert message == "Not connected to any database"
        assert result == 400
