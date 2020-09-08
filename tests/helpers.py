import hashlib
import json
import os
import time
import uuid

from web3 import Web3
from eth_account import Account
from web3.datastructures import AttributeDict

from tests.ddos.ddo_event_sample import ddo_event_sample

rpc = os.environ.get('EVENTS_RPC', None)
WEB3_INSTANCE = Web3(Web3.HTTPProvider(rpc))


test_account1 = Account.from_key(os.environ.get('EVENTS_TESTS_PRIVATE_KEY', None))
test_account2 = Account.from_key(os.environ.get('EVENTS_TESTS_PRIVATE_KEY2', None))
ecies_account = Account.from_key(os.environ.get('EVENTS_ECIES_PRIVATE_KEY', None))


def web3():
    return WEB3_INSTANCE


def ddo_contract():
    contract_address = os.environ.get('EVENTS_CONTRACT_ADDRESS', None)
    path = './aquarius/artifacts/DDO.json'
    abi_json = json.load(open(path))
    return web3().eth.contract(address=contract_address, abi=abi_json['abi'])


def prepare_did(text):
    prefix = 'did:op:'
    if text.startswith(prefix):
        text = text[len(prefix):]
    return text


def new_did(seed):
    _id = hashlib.sha3_256(
        (json.dumps(seed).replace(" ", "")).encode('utf-8')).hexdigest()
    return f'did:op:{_id}'


def new_ddo(address, ddo=None):
    _ddo = ddo if ddo else ddo_event_sample.copy()
    if 'publicKey' not in _ddo or not _ddo['publicKey']:
        _ddo['publicKey'] = [{'owner': ''}]
    _ddo['publicKey'][0]['owner'] = address
    _ddo['random'] = str(uuid.uuid4())
    _ddo['id'] = new_did(str(uuid.uuid4()))
    return AttributeDict(_ddo)


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
    f = getattr(ddo_contract().events, event_name)().createFilter(fromBlock=block)
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


def send_tx(fn_name, tx_args, account):
    web3().eth.defaultAccount = account.address
    txn_hash = getattr(ddo_contract().functions, fn_name)(*tx_args).transact()
    txn_receipt = web3().eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt


def send_create_update_tx(name, did, flags, data, account):
    print(f'{name}DDO {did} with flags: {flags} from {account.address}')
    did = prepare_did(did)
    print('*****************************************************************************\r\n')
    print(did)
    print('*****************************************************************************\r\n')
    r = send_tx(name, (did, flags, data), account)
    event_name = 'DDOCreated' if name == 'create' else 'DDOUpdated'
    events = getattr(ddo_contract().events, event_name)().processReceipt(r)
    print(f'got {event_name} logs: {events}')
    return r


def transfer_ownership(did, new_owner, account):
    print(f'transfer_ownership {did} to {new_owner}')
    did = prepare_did(did)
    web3().eth.defaultAccount = account.address
    txn_hash = ddo_contract().functions.transferOwnership(did, new_owner).transact()
    txn_receipt = web3().eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt
