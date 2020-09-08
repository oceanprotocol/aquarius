#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json
import lzma

import ecies
from web3 import Web3

import eth_keys

from tests.helpers import (
    web3,
    new_ddo,
    test_account1,
    send_create_update_tx,
    test_account2,
    ecies_account,
    get_ddo,
    get_event,
    transfer_ownership)


def run_test(client, base_ddo_url, events_instance, flags=None, encryption_key=None):
    block = web3().eth.blockNumber
    _ddo = new_ddo(test_account1.address)
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

    send_create_update_tx('create', did, bytes([_flags]), data, test_account1)
    get_event('DDOCreated', block, did, 30)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did

    _ddo['service'][0]['attributes']['main']['name'] = 'Updated ddo by event'
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    if flags is not None:
        data = lzma.compress(data)

    if encryption_key is not None:
        key = eth_keys.KeyAPI.PrivateKey(encryption_key)
        data = ecies.encrypt(key.public_key.to_hex(), data)

    send_create_update_tx('update', did, bytes([_flags]), data, test_account1)
    get_event('DDOUpdated', block, did, 30)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did
    assert published_ddo['service'][0]['attributes']['main']['name'] == 'Updated ddo by event'


def test_publish_and_update_ddo(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object)


def test_publish_and_update_ddo_with_lzma(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 0)


def test_publish_and_update_ddo_with_lzma_and_ecies(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 0, ecies_account.privateKey)


def test_publish_and_transfer_ownership(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account1.address)
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx('create', did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did

    transfer_ownership(did, test_account2.address, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did
    assert published_ddo['publicKey'][0]['owner'] == test_account2.address
