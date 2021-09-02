#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import elasticsearch
from web3 import Web3

from aquarius.constants import BaseURLs
from aquarius.events.constants import EVENT_METADATA_CREATED
from aquarius.run import get_status
from tests.ddo_samples_invalid import json_dict_no_valid_metadata
from tests.ddos.ddo_sample1 import json_dict
from tests.ddos.ddo_sample_updates import json_before
from tests.helpers import (
    get_event,
    get_web3,
    new_ddo,
    send_create_update_tx,
    test_account1,
    run_request,
    run_request_get_data,
)
from unittest.mock import patch


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
            "api/v1/aquarius/assets/metadata/1", content_type="application/json"
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
        mock.side_effect = elasticsearch.exceptions.TransportError("Boom!")
        rv = run_request(client.post, query_url, {"didList": [1]})
        assert rv.status_code == 507
        assert (
            rv.json["error"]
            == "Received elasticsearch TransportError. Please refine the search."
        )


def test_chains_list_exceptions(client, chains_url):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = elasticsearch.exceptions.NotFoundError("Boom!")
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
        mock.side_effect = elasticsearch.exceptions.NotFoundError("Boom!")
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
