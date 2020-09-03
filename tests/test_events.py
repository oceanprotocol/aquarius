#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import hashlib
import json
import os
import time
import lzma
import uuid

import ecies
from web3 import Web3

from tests.ddos.ddo_event_sample import ddo_event_sample
from eth_account import Account
import eth_keys

privateKey = os.environ.get('EVENTS_TESTS_PRIVATE_KEY', None)
rpc = os.environ.get('EVENTS_RPC', None)
contract_address = os.environ.get('EVENTS_CONTRACT_ADDRESS', None)
ecies_privateKey = os.environ.get('EVENTS_ECIES_PRIVATE_KEY', None)
web3 = Web3(Web3.HTTPProvider(rpc))
path = './aquarius/artifacts/DDO.json'
abi_json = json.load(open(path))
events_contract = web3.eth.contract(address=contract_address, abi=abi_json['abi'])

account1 = Account.from_key(privateKey)
privateKey2 = os.environ.get('EVENTS_TESTS_PRIVATE_KEY2', None)
account2 = Account.from_key(privateKey2)
ecies_account = Account.from_key(ecies_privateKey)


def new_did(seed):
    _id = hashlib.sha3_256(
        (json.dumps(seed).replace(" ", "")).encode('utf-8')).hexdigest()
    return f'did:op:{_id}'


def new_ddo(address):
    _ddo = ddo_event_sample.copy()
    _ddo['publicKey'][0]['owner'] = address
    _ddo['random'] = str(uuid.uuid4())
    _ddo['id'] = new_did(str(uuid.uuid4()))
    return _ddo


def get_ddo(client, base_ddo_url, did):
    rv = client.get(
        base_ddo_url + f'/{did}',
        content_type='application/json'
    )
    try:
        fetched_ddo = json.loads(rv.data.decode('utf-8'))
        return fetched_ddo
    except (Exception, ValueError) as e:
        print(f'Error fetching cached ddo {did}: {e}.'
              f'\nresponse data was: {rv.data}')
        return None


def get_event(event_name, block, did, timeout=45):
    did = prepare_did(did)
    start = time.time()
    f = getattr(events_contract.events, event_name)().createFilter(fromBlock=block)
    logs = []
    while not logs:
        logs = f.get_all_entries()
        if not logs:
            time.sleep(0.2)

        if time.time() - start > timeout:
            break

    print(f'done waiting for {event_name} event, got: {logs}')
    assert logs, 'no events found {event_name}, block {block}.'
    _log = None
    for log in logs:
        if log.args.did.hex() == did:
            _log = log
            break
    return _log


def send_create_update_tx(name, did, flags, data, account):
    print(f'{name}DDO {did} with flags: {flags} from {account.address}')
    did = prepare_did(did)
    print('*****************************************************************************\r\n')
    print(did)
    print('*****************************************************************************\r\n')
    r = send_tx(name, (did, flags, data), account)
    event_name = 'DDOCreated' if name == 'create' else 'DDOUpdated'
    events = getattr(events_contract.events, event_name)().processReceipt(r)
    print(f'got {event_name} logs: {events}')
    return r


def send_tx(fn_name, tx_args, account):
    web3.eth.defaultAccount = account.address
    txn_hash = getattr(events_contract.functions, fn_name)(*tx_args).transact()
    txn_receipt = web3.eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt


def transfer_ownership(did, new_owner, account):
    print(f'transfer_ownership {did} to {new_owner}')
    did = prepare_did(did)
    web3.eth.defaultAccount = account.address
    txn_hash = events_contract.functions.transferOwnership(did, new_owner).transact()
    txn_receipt = web3.eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt


def prepare_did(text):
    prefix = 'did:op:'
    if text.startswith(prefix):
        text = text[len(prefix):]
    return text


def run_test(client, base_ddo_url, events_instance, flags=None, encryption_key=None):
    block = web3.eth.blockNumber
    _ddo = new_ddo(account1.address)
    did = _ddo['id']
    ddo_string = json.dumps(_ddo)
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

    send_create_update_tx('create', did, bytes([_flags]), data, account1)
    get_event('DDOCreated', block, did, 30)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did

    _ddo['service'][0]['attributes']['main']['name'] = 'Updated ddo by event'
    ddo_string = json.dumps(_ddo)
    data = Web3.toBytes(text=ddo_string)
    if flags is not None:
        data = lzma.compress(data)

    if encryption_key is not None:
        key = eth_keys.KeyAPI.PrivateKey(encryption_key)
        data = ecies.encrypt(key.public_key.to_hex(), data)

    send_create_update_tx('update', did, bytes([_flags]), data, account1)
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
    _ddo = new_ddo(account1.address)
    did = _ddo['id']
    ddo_string = json.dumps(_ddo)
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx('create', did, bytes([0]), data, account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did

    transfer_ownership(did, account2.address, account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo['id'] == did
    assert published_ddo['publicKey'][0]['owner'] == account2.address
