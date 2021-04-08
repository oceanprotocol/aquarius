#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import lzma

import ecies
from web3 import Web3

import eth_keys

from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from ocean_lib.ocean.ocean_exchange import OceanExchange
from aquarius.events.util import deploy_datatoken
from ocean_lib.ocean.util import get_contracts_addresses
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.web3_internal.wallet import Wallet
from tests.helpers import (
    get_web3,
    new_ddo,
    test_account1,
    test_account3,
    send_create_update_tx,
    ecies_account,
    get_ddo,
    get_event,
)

_NETWORK = "ganache"


def run_test(client, base_ddo_url, events_instance, flags=None, encryption_key=None):
    web3 = get_web3()
    block = web3.eth.blockNumber
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    _flags = flags or 0
    if flags is not None:
        data = lzma.compress(data)
        # mark bit 1
        _flags = _flags | 1

    if encryption_key is not None:
        # ecies encrypt - bit 2
        _flags = _flags | 2
        key = eth_keys.KeyAPI.PrivateKey(encryption_key)
        data = ecies.encrypt(key.public_key.to_hex(), data)

    send_create_update_tx("create", did, bytes([_flags]), data, test_account1)
    get_event(EVENT_METADATA_CREATED, block, did)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did

    _ddo["service"][0]["attributes"]["main"]["name"] = "Updated ddo by event"
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    if flags is not None:
        data = lzma.compress(data)

    if encryption_key is not None:
        key = eth_keys.KeyAPI.PrivateKey(encryption_key)
        data = ecies.encrypt(key.public_key.to_hex(), data)

    send_create_update_tx("update", did, bytes([_flags]), data, test_account1)
    get_event(EVENT_METADATA_UPDATED, block, did)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert (
        published_ddo["service"][0]["attributes"]["main"]["name"]
        == "Updated ddo by event"
    )


def test_publish_and_update_ddo(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object)


def test_publish_and_update_ddo_with_lzma(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 0)


def test_publish_and_update_ddo_with_lzma_and_ecies(
    client, base_ddo_url, events_object
):
    run_test(client, base_ddo_url, events_object, 0, ecies_account.privateKey)


def test_publish(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did


def test_publish_unallowed_address(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account3, get_web3(), "dt.0")
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx("create", did, bytes([0]), data, test_account3)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo is None


def test_fixed_rate_events(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)

    dt_address_2 = deploy_datatoken(
        get_web3(), test_account1.privateKey, "dt.1", "dt.1", test_account1.address
    )
    ox = OceanExchange(
        dt_address_2, _get_exchange_address(), ConfigProvider.get_config()
    )
    test_account1_wallet = Wallet(get_web3(), private_key=test_account1.privateKey)
    x_id = ox.create(_ddo["dataToken"], 0.9, test_account1_wallet)
    events_object._process_pool_events()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["price"]["exchange_id"] == "0x" + x_id.hex()


def _get_exchange_address():
    return get_contracts_addresses(_NETWORK, ConfigProvider.get_config())[
        FixedRateExchange.CONTRACT_NAME
    ]
