#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from tests.helpers import run_request
from unittest.mock import patch

from tests.ddos.ddo_sample1_v4 import json_dict


def test_validate_credentials(client_with_no_data, base_ddo_url):
    json_valid_copy = json_dict.copy()
    json_valid_copy["credentials"] = {
        "allow": [{"type": "address", "values": ["0x123", "0x456A"]}],
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}],
    }

    post = run_request(
        client_with_no_data.post,
        base_ddo_url + "/validate",
        data=json_valid_copy,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert post.hash != b""

    # still valid if only one of "allow" and "deny are present
    json_valid_copy["credentials"] = {
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}]
    }

    post = run_request(
        client_with_no_data.post,
        base_ddo_url + "/validate",
        data=json_valid_copy,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert post.hash != b""

    invalid_credentials = [
        {"allow": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"deny": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"allow": [{"type": "address"}]},  # missing values
        {"allow": [{"values": "not_an_array"}]},  # missing type
    ]

    for invalid_credential in invalid_credentials:
        json_valid_copy["credentials"] = invalid_credential

        post = run_request(
            client_with_no_data.post,
            base_ddo_url + "/validate",
            data=json_valid_copy,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert post.status_code == 400


def test_validate_remote_noversion(client_with_no_data, base_ddo_url):
    post = run_request(
        client_with_no_data.post,
        base_ddo_url + "/validate",
        data={},
        headers={"Content-Type": "application/octet-stream"},
    )
    assert post.status_code == 400
    assert post.json[0]["message"] == "no version provided for DDO."


def test_validate_error(client, base_ddo_url, monkeypatch):
    with patch("aquarius.app.assets.validate_dict") as mock:
        mock.side_effect = Exception("Boom!")
        rv = run_request(
            client.post,
            base_ddo_url + "/validate",
            data={"service": [], "test": "test", "version": "4.0.0"},
            headers={"Content-Type": "application/octet-stream"},
        )
        assert rv.status_code == 500
        assert rv.json["error"] == "Encountered error when validating asset: Boom!."


def test_validate_error_remote(client, base_ddo_url, monkeypatch):
    rv = run_request(
        client.post,
        base_ddo_url + "/validate",
        data={"@context": ["test"], "services": "bla", "version": "4.0.0"},
        headers={"Content-Type": "application/octet-stream"},
    )
    assert rv.status_code == 400
    assert "Value does not conform to Shape schema" in rv.json["errors"]["services"]
    assert "ServiceShape" in rv.json["errors"]["services"]
