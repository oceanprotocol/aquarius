#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json

from aquarius.run import get_status, get_version
from tests.helpers import run_request, run_request_get_data, run_request_octet


def test_version(client):
    """Test version in root endpoint"""
    rv = client.get("/")
    assert json.loads(rv.data.decode("utf-8"))["software"] == "Aquarius"
    assert json.loads(rv.data.decode("utf-8"))["version"] == get_version()


def test_health(client):
    """Test health check endpoint"""
    rv = client.get("/health")
    assert rv.data.decode("utf-8") == get_status()[0]


def test_spec(client):
    result = run_request_get_data(client.get, "/spec")
    assert "version" in result["info"]
    assert "title" in result["info"]
    assert "description" in result["info"]
    assert "connected" in result["info"]


def test_invalid_requests(client_with_no_data, base_ddo_url, query_url):
    response = run_request(client_with_no_data.post, query_url, "not a dict request")
    assert response.status == "400 BAD REQUEST"

    response = run_request_octet(
        client_with_no_data.post, base_ddo_url + "/validate", "not a dict request"
    )
    assert response.status == "400 BAD REQUEST"


def test_conversion(client, validation_url):
    response = run_request(client.get, validation_url + "/schema?version=blabla")
    assert response.status == "404 NOT FOUND"

    response = run_request(client.get, validation_url + "/schema?version=4.1.0")
    assert response.status == "200 OK"

    response = run_request(client.get, validation_url + "/schema")
    assert response.status == "200 OK"
    response_json = response.json
    assert response_json["version"]["maxLength"] == 16
    response.json["credentials"]["deny"]["type"]["maxLength"] == 256
