#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from unittest.mock import patch

from tests.ddos.ddo_sample1_v4 import json_dict
from tests.helpers import run_request_octet


def test_validate_credentials(client_with_no_data, base_ddo_url):
    json_valid_copy = json_dict.copy()
    json_valid_copy["credentials"] = {
        "allow": [{"type": "address", "values": ["0x123", "0x456A"]}],
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}],
    }
    post = run_request_octet(
        client_with_no_data.post,
        base_ddo_url + "/validate",
        data=json.dumps(json_valid_copy),
    )
    data = post.get_json()
    assert data["hash"] != b""

    # still valid if only one of "allow" and "deny are present
    json_valid_copy["credentials"] = {
        "deny": [{"type": "address", "values": ["0x2222", "0x333"]}]
    }

    post = run_request_octet(
        client_with_no_data.post,
        base_ddo_url + "/validate",
        data=json.dumps(json_valid_copy),
    )
    data = post.get_json()
    assert data["hash"] != b""

    invalid_credentials = [
        {"allow": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"deny": [{"type": "address", "value": ["0x123", "0x456A"]}]},
        {"allow": [{"type": "address"}]},  # missing values
        {"allow": [{"values": "not_an_array"}]},  # missing type
    ]

    for invalid_credential in invalid_credentials:
        json_valid_copy["credentials"] = invalid_credential

        post = run_request_octet(
            client_with_no_data.post,
            base_ddo_url + "/validate",
            data=json.dumps(json_valid_copy),
        )
        assert post.status_code == 400


def test_validate_remote_noversion(client_with_no_data, base_ddo_url):
    post = run_request_octet(
        client_with_no_data.post, base_ddo_url + "/validate", data=json.dumps({})
    )
    data = post.get_json()
    assert post.status_code == 400
    assert data[0]["message"] == "no version provided for DDO."


def test_validate_error(client, base_ddo_url, monkeypatch):
    with patch("aquarius.app.assets.validate_dict") as mock:
        mock.side_effect = Exception("Boom!")
        rv = run_request_octet(
            client.post,
            base_ddo_url + "/validate",
            data=json.dumps({"service": [], "test": "test", "version": "4.0.0"}),
        )
        data = rv.get_json()
        assert rv.status_code == 500
        assert data["error"] == "Encountered error when validating asset: Boom!."


def test_validate_error_remote(client, base_ddo_url, monkeypatch):
    rv = run_request_octet(
        client.post,
        base_ddo_url + "/validate",
        data=json.dumps({"@context": ["test"], "services": "bla", "version": "4.0.0"}),
    )
    data = rv.get_json()
    assert rv.status_code == 400
    assert "Value does not conform to Shape schema" in data["errors"]["services"]
    assert "ServiceShape" in data["errors"]["services"]
