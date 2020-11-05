import json
import os
import time
import uuid

from eth_utils import remove_0x_prefix, add_0x_prefix
from web3 import Web3
from eth_account import Account
from web3.datastructures import AttributeDict

from aquarius.events.util import get_metadata_contract, deploy_datatoken
from aquarius.events.constants import EVENT_METADATA_CREATED, EVENT_METADATA_UPDATED
from tests.ddos.ddo_event_sample import ddo_event_sample

rpc = os.environ.get('EVENTS_RPC', None)
WEB3_INSTANCE = Web3(Web3.HTTPProvider(rpc))


test_account1 = Account.privateKeyToAccount(os.environ.get('EVENTS_TESTS_PRIVATE_KEY', None))
test_account2 = Account.privateKeyToAccount(os.environ.get('EVENTS_TESTS_PRIVATE_KEY2', None))
test_account3 = Account.privateKeyToAccount(os.environ.get('EVENTS_TESTS_PRIVATE_KEY3', None))
ecies_account = Account.privateKeyToAccount(os.environ.get('EVENTS_ECIES_PRIVATE_KEY', None))


def get_web3():
    """
    Return the web3 url.

    Args:
    """
    return WEB3_INSTANCE


def prepare_did(text):
    """
    Prepares the text for the given text.

    Args:
        text: (str): write your description
    """
    prefix = 'did:op:'
    if text.startswith(prefix):
        text = text[len(prefix):]
    return add_0x_prefix(text)


def new_did(dt_address):
    """
    Create a new did.

    Args:
        dt_address: (str): write your description
    """
    return f'did:op:{remove_0x_prefix(dt_address)}'


def new_ddo(account, web3, name, ddo=None):
    """
    Create a new dict

    Args:
        account: (todo): write your description
        web3: (todo): write your description
        name: (str): write your description
        ddo: (todo): write your description
    """
    _ddo = ddo if ddo else ddo_event_sample.copy()
    if 'publicKey' not in _ddo or not _ddo['publicKey']:
        _ddo['publicKey'] = [{'owner': ''}]
    _ddo['publicKey'][0]['owner'] = account.address
    _ddo['random'] = str(uuid.uuid4())
    dt_address = deploy_datatoken(web3, account.privateKey, name, name, account.address)
    _ddo['id'] = new_did(dt_address)
    _ddo['dataToken'] = dt_address
    return AttributeDict(_ddo)


def get_ddo(client, base_ddo_url, did):
    """
    Download a ddo from a specific ddo.

    Args:
        client: (todo): write your description
        base_ddo_url: (str): write your description
        did: (int): write your description
    """
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
    """
    Get the event.

    Args:
        event_name: (str): write your description
        block: (bool): write your description
        did: (str): write your description
        timeout: (int): write your description
    """
    did = prepare_did(did)
    start = time.time()
    f = getattr(get_metadata_contract(get_web3()).events, event_name)().createFilter(fromBlock=block)
    logs = []
    while not logs:
        logs = f.get_all_entries()
        if not logs:
            time.sleep(0.2)

        if time.time() - start > timeout:
            break

    assert logs, 'no events found {event_name}, block {block}.'
    print(f'done waiting for {event_name} event, got {len(logs)} logs, and datatokens: {[l.args.dataToken for l in logs]}')
    _log = None
    for log in logs:
        if log.args.dataToken == did:
            _log = log
            break
    assert _log, f'event log not found: {event_name}, {block}, {did}'
    return _log


def send_tx(fn_name, tx_args, account):
    """
    This interface is used to send a transaction.

    Args:
        fn_name: (str): write your description
        tx_args: (dict): write your description
        account: (str): write your description
    """
    get_web3().eth.defaultAccount = account.address
    txn_hash = getattr(get_metadata_contract(get_web3()).functions, fn_name)(*tx_args).transact()
    txn_receipt = get_web3().eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt


def send_create_update_tx(name, did, flags, data, account):
    """
    Send a did to an account.

    Args:
        name: (str): write your description
        did: (str): write your description
        flags: (todo): write your description
        data: (todo): write your description
        account: (str): write your description
    """
    print(f'{name}DDO {did} with flags: {flags} from {account.address}')
    did = prepare_did(did)
    print('*****************************************************************************\r\n')
    print(did)
    print('*****************************************************************************\r\n')
    r = send_tx(name, (did, flags, data), account)
    event_name = EVENT_METADATA_CREATED if name == 'create' else EVENT_METADATA_UPDATED
    events = getattr(get_metadata_contract(get_web3()).events, event_name)().processReceipt(r)
    # print(f'got {event_name} logs: {events}')
    return r
