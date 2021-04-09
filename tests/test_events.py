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
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.data_token import DataToken
from ocean_lib.ocean.ocean_exchange import OceanExchange
from aquarius.events.util import deploy_datatoken
from ocean_lib.ocean.util import get_contracts_addresses, get_bfactory_address
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.web3_internal.wallet import Wallet
from ocean_lib.ocean.util import to_base_18
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


def do_publish(client, base_ddo_url, events_object, symbol="dt.0"):
    _ddo = new_ddo(test_account1, get_web3(), symbol)
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    return _ddo, get_ddo(client, base_ddo_url, did)


def test_publish(client, base_ddo_url, events_object):
    _ddo, published_ddo = do_publish(client, base_ddo_url, events_object)
    assert published_ddo["id"] == _ddo.id


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
    _ddo, published_ddo = do_publish(client, base_ddo_url, events_object)
    dt_address_2 = deploy_datatoken(
        get_web3(), test_account1.privateKey, "dt.1", "dt.1", test_account1.address
    )
    ox = OceanExchange(
        dt_address_2, _get_exchange_address(), ConfigProvider.get_config()
    )
    test_account1_wallet = Wallet(get_web3(), private_key=test_account1.privateKey)
    x_id = ox.create(_ddo["dataToken"], 0.9, test_account1_wallet)
    events_object._process_pool_events()
    published_ddo = get_ddo(client, base_ddo_url, _ddo.id)
    assert published_ddo["price"]["exchange_id"] == "0x" + x_id.hex()

    # TODO: test rate changed event once available in ocean.py


def test_pool_events(client, base_ddo_url, events_object):
    _ddo, published_ddo = do_publish(client, base_ddo_url, events_object)
    _ddo2, published_ddo2 = do_publish(
        client, base_ddo_url, events_object, symbol="dt.1"
    )
    T1 = DataToken(_ddo["dataToken"])
    T2 = DataToken(_ddo2["dataToken"])

    assert published_ddo["price"]["type"] == ""
    assert published_ddo["price"]["pools"] == []
    assert published_ddo2["price"]["type"] == ""
    assert published_ddo2["price"]["pools"] == []

    alice = test_account1
    bob = test_account3
    alice_wallet = Wallet(get_web3(), private_key=alice.privateKey)
    bob_wallet = Wallet(get_web3(), private_key=bob.privateKey)

    T1.mint(alice.address, to_base_18(1000.0), alice_wallet)
    T2.mint(alice.address, to_base_18(1000.0), alice_wallet)

    factory_address = get_bfactory_address(_NETWORK)
    factory = BFactory(factory_address)
    pool_address = factory.newBPool(from_wallet=alice_wallet)
    pool = BPool(pool_address)

    T1.approve(pool.address, to_base_18(90.0), from_wallet=alice_wallet)
    T2.approve(pool.address, to_base_18(10.0), from_wallet=alice_wallet)
    T1.approve(pool.address, to_base_18(100.0), from_wallet=bob_wallet)
    T2.approve(pool.address, to_base_18(100.0), from_wallet=bob_wallet)

    pool.bind(T1.address, to_base_18(90.0), to_base_18(9.0), from_wallet=alice_wallet)
    pool.bind(T2.address, to_base_18(10.0), to_base_18(1.0), from_wallet=alice_wallet)

    # alice gives bob some freshly minted tokens, to help him join the pool
    T1.transfer(bob_wallet.address, to_base_18(100.0), from_wallet=alice_wallet)
    T2.transfer(bob_wallet.address, to_base_18(100.0), from_wallet=alice_wallet)

    pool.finalize(from_wallet=alice_wallet)

    # bob joins the pool
    pool.joinPool(
        poolAmountOut_base=to_base_18(10.0),  # 10 BPT
        maxAmountsIn_base=[to_base_18(100.0), to_base_18(100.0)],
        from_wallet=bob_wallet,
    )

    events_object._process_pool_events()

    # retrieve the published ddos again
    published_ddo = get_ddo(client, base_ddo_url, _ddo.id)
    published_ddo2 = get_ddo(client, base_ddo_url, _ddo2.id)

    assert published_ddo["price"]["type"] == "pool"
    assert published_ddo["price"]["pools"] == [pool.address]
    assert published_ddo2["price"]["type"] == ""
    assert published_ddo2["price"]["pools"] == []


def _get_exchange_address():
    return get_contracts_addresses(_NETWORK, ConfigProvider.get_config())[
        FixedRateExchange.CONTRACT_NAME
    ]
