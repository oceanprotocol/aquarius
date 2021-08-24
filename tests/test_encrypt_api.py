#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import lzma

import ecies
from web3 import Web3
import eth_keys
from unittest.mock import patch

from aquarius.events.constants import EVENT_METADATA_CREATED
from tests.helpers import (
    get_event,
    get_web3,
    new_ddo,
    send_create_update_tx,
    test_account1,
    ecies_account,
    run_request_get_data
)


def test_encrypt_ddo(client, base_ddo_url, events_object):
    block = get_web3().eth.block_number
    ddo = new_ddo(test_account1, get_web3(), "encrypt_test")
    ddo_string = json.dumps(dict(ddo.items()))
    compressed_ddo = lzma.compress(Web3.toBytes(text=ddo_string))
    _response = client.post(
        base_ddo_url + "/encrypt",
        data=compressed_ddo,
        content_type="application/octet-stream",
    )
    assert _response.status_code == 200
    encrypted_ddo = _response.data
    key = eth_keys.KeyAPI.PrivateKey(ecies_account.key)
    decrypted_ddo = ecies.decrypt(key.to_hex(), Web3.toBytes(encrypted_ddo))
    assert decrypted_ddo == compressed_ddo
    # test encrypt as hex
    _response_hex = client.post(
        base_ddo_url + "/encryptashex",
        data=compressed_ddo,
        content_type="application/octet-stream",
    )
    assert _response_hex.status_code == 200
    encrypted_ddo_hex = _response_hex.data.decode("utf-8")
    decrypted_ddo_from_hex = ecies.decrypt(
        key.to_hex(), Web3.toBytes(hexstr=encrypted_ddo_hex)
    )
    assert decrypted_ddo_from_hex == compressed_ddo

    send_create_update_tx(
        "create", ddo["id"], bytes([3]), Web3.toBytes(encrypted_ddo), test_account1
    )
    get_event(EVENT_METADATA_CREATED, block, ddo["id"])
    events_object.process_current_blocks()
    assert (
        len(
            run_request_get_data(
                client.post,
                base_ddo_url + "/query",
                {
                    "query": {
                        "query_string": {
                            "query": ddo["dataToken"],
                            "default_field": "dataToken",
                        }
                    }
                },
            )["hits"]["hits"]
        )
        > 0
    )

    result = run_request_get_data(
        client.get, "api/v1/aquarius/assets/metadata/" + ddo["id"]
    )
    assert "main" in result
    assert "name" in result["main"]
    assert result["main"]["name"] == "Event DDO sample"


def test_encrypt_ddo_content_failures(client, base_ddo_url, events_object, monkeypatch):
    _response = client.post(
        base_ddo_url + "/encrypt",
        data="irrelevant",
        content_type="application/not-octet-stream",
    )
    assert _response.status_code == 400

    monkeypatch.delenv("EVENTS_ECIES_PRIVATE_KEY")
    _response = client.post(
        base_ddo_url + "/encrypt",
        data="irrelevant",
        content_type="application/octet-stream",
    )
    assert _response.status_code == 400

    monkeypatch.setenv("EVENTS_ECIES_PRIVATE_KEY", "thisIsNotValid")
    _response = client.post(
        base_ddo_url + "/encrypt",
        data="irrelevant",
        content_type="application/octet-stream",
    )
    assert _response.status_code == 400


def test_encrypt_wrong(client, base_ddo_url, monkeypatch):
    # unset ecies private key should make the encrypt function return False
    monkeypatch.delenv("EVENTS_ECIES_PRIVATE_KEY")

    _response = client.post(
        base_ddo_url + "/encrypt",
        data="irrelevant",
        content_type="application/octet-stream",
    )
    assert _response.status_code == 400

    _response = client.post(
        base_ddo_url + "/encryptashex",
        data="irrelevant",
        content_type="application/octet-stream",
    )
    assert _response.status_code == 400


def test_encrypt_exceptions(client, base_ddo_url):
    with patch('aquarius.app.assets.encrypt_data') as mock:
        mock.side_effect = Exception('Boom!')
        _response = client.post(
            base_ddo_url + "/encrypt",
            data="irrelevant",
            content_type="application/octet-stream",
        )
        assert _response.status_code == 500

    with patch('aquarius.app.assets.encrypt_data') as mock:
        mock.side_effect = Exception('Boom!')
        _response = client.post(
            base_ddo_url + "/encryptashex",
            data="irrelevant",
            content_type="application/octet-stream",
        )
        assert _response.status_code == 500
