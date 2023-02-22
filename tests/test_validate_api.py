#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from requests.models import Response
from unittest.mock import patch, Mock

from aquarius.ddo_checker.shacl_checker import CURRENT_VERSION
from tests.ddos.ddo_sample1_v4 import json_dict
from tests.helpers import run_request_octet, run_request


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
            data=json.dumps(
                {"service": [], "test": "test", "version": CURRENT_VERSION}
            ),
        )
        data = rv.get_json()
        assert rv.status_code == 500
        assert data["error"] == "Encountered error when validating asset: Boom!."


def test_validate_error_remote(client, base_ddo_url, monkeypatch):
    rv = run_request_octet(
        client.post,
        base_ddo_url + "/validate",
        data=json.dumps(
            {"@context": ["test"], "services": "bla", "version": CURRENT_VERSION}
        ),
    )
    data = rv.get_json()
    assert rv.status_code == 400
    assert "Value does not conform to Shape schema" in data["errors"]["services"]
    assert "ServiceShape" in data["errors"]["services"]


def test_non_octet_non_dict(client, base_ddo_url, monkeypatch):
    rv = run_request(client.post, base_ddo_url + "/validate")
    data = rv.get_json()
    assert rv.status_code == 400
    assert (
        data["error"]
        == "Invalid request content type: should be application/octet-stream"
    )

    rv = run_request_octet(client.post, base_ddo_url + "/validate", data="not a dict")
    data = rv.get_json()
    assert rv.status_code == 400
    assert (
        data["error"]
        == "Invalid payload. The request could not be converted into a dict."
    )


def test_validate_through_rbac(client, base_ddo_url, monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "test")

    with patch("requests.post") as mock:
        response = Mock(spec=Response)
        response.json.return_value = False
        mock.return_value = response

        rv = run_request_octet(
            client.post, base_ddo_url + "/validate", data=json.dumps({"test": "test"})
        )

        data = rv.get_json()
        assert rv.status_code == 400
        assert data["error"] == "DDO marked invalid by the RBAC server."
