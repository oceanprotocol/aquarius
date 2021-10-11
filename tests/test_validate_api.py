#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json

from tests.ddos.ddo_sample_updates import json_before, json_valid
from tests.helpers import run_request
from unittest.mock import patch


def test_validate(client_with_no_data, base_ddo_url):
    post = run_request(client_with_no_data.post, base_ddo_url + "/validate", data={})
    assert post.status_code == 200
    assert (
        post.data == b'[{"message":"\'main\' is a required property","path":""}]\n'
    )  # noqa
    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate", data=json_valid
    )
    assert post.data == b"true\n"


def test_validate_credentials(client_with_no_data, base_ddo_url):
    json_valid_copy = json_valid.copy()
    json_valid_copy["credentials"] = {
        "allow": [{"type": "address", "values": ["0x123", "0x456A"]}],
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}],
    }

    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate", data=json_valid_copy
    )
    assert post.data == b"true\n"

    # still valid if only one of "allow" and "deny are present
    json_valid_copy["credentials"] = {
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}],
    }

    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate", data=json_valid_copy
    )
    assert post.data == b"true\n"

    invalid_credentials = [
        {"allow": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"deny": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"allow": [{"type": "address", "values": "not_an_array"}]},
        {"allow": [{"type": "address"}]},  # missing values
        {"allow": [{"values": "not_an_array"}]},  # missing type
    ]

    for invalid_credential in invalid_credentials:
        json_valid_copy["credentials"] = invalid_credential

        post = run_request(
            client_with_no_data.post, base_ddo_url + "/validate", data=json_valid_copy
        )
        assert post.data != b"true\n"


def test_validate_remote(client_with_no_data, base_ddo_url):
    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate-remote", data={}
    )
    assert post.status_code == 200
    assert post.json[0]["message"] == "missing `service` key in data."

    # main key missing from metadata service - should fail from Aqua
    val = json_before["service"][2]["attributes"].pop("main")
    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate-remote", data=json_before
    )
    assert post.status_code == 200

    # main key empty in metadata service - should fail from DDO Checker
    json_before["service"][2]["attributes"]["main"] = {}
    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate-remote", data=json_before
    )
    assert post.status_code == 200
    assert json.loads(post.data)[0]["message"] == "'name' is a required property"

    # putting back the correct value in metadata main service - should pass
    json_before["service"][2]["attributes"]["main"] = val
    post = run_request(
        client_with_no_data.post, base_ddo_url + "/validate-remote", data=json_before
    )
    assert post.data == b"true\n"


def test_validate_error(client, base_ddo_url, monkeypatch):
    with patch("aquarius.app.assets.validate_dict") as mock:
        mock.side_effect = Exception("Boom!")
        rv = run_request(client.post, base_ddo_url + "/validate", data={"test": "test"})
        assert rv.status_code == 500
        assert rv.json["error"] == "Encountered error when validating metadata: Boom!."


def test_validate_error_remote(client, base_ddo_url, monkeypatch):
    rv = run_request(
        client.post, base_ddo_url + "/validate-remote", data={"service": "bla"}
    )
    assert rv.status_code == 500
    assert (
        rv.json["error"]
        == "Encountered error when validating asset: string indices must be integers."
    )
