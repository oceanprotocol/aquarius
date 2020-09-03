#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
import logging
import os
import time
import lzma as Lzma
import uuid

import ecies
from plecos import plecos
from web3 import Web3
from web3.contract import ConciseContract

from aquarius.app.util import validate_date_format
from aquarius.app.auth_util import get_signer_address
from aquarius.constants import BaseURLs
from aquarius.run import get_status, get_version
from tests.ddos.ddo_event_sample import ddo_event_sample
from eth_account.messages import encode_defunct
from eth_account import Account
import eth_keys


ddo_contract_address = '0x312213d6f6b5FCF9F56B7B8946A6C727Bf4Bc21f'
# privateKey = os.environ.get('EVENTS_TESTS_PRIVATE_KEY',None)
rpc = os.environ.get('EVENTS_RPC', None)
contract_address = os.environ.get('EVENTS_CONTRACT_ADDRESS',None)
ecies_privateKey = os.environ.get('EVENTS_ECIES_PRIVATE_KEY',None)
web3 = Web3(Web3.HTTPProvider(rpc))
path = './aquarius/artifacts/DDO.json'
data=json.load(open(path))
events_contract=web3.eth.contract(address=contract_address, abi=data['abi'])
ccontract = ConciseContract(events_contract)

_address = '0xe2DD09d719Da89e5a3D0F2549c7E24566e947260'
privateKey = '0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58'
account1 = Account.from_key(privateKey)
assert account1.address == _address

privateKey2 = os.environ.get('EVENTS_TESTS_PRIVATE_KEY2',None)
account2 = Account.from_key(privateKey2)


def new_did(seed):
    _id = hashlib.sha3_256(
        (json.dumps(seed).replace(" ", "")).encode('utf-8')).hexdigest()
    return f'did:op:{_id}'


def get_ddo(client, base_ddo_url, did):
    rv = client.get(
        base_ddo_url + f'/{did}',
        content_type='application/json'
    )
    fetched_ddo = json.loads(rv.data.decode('utf-8'))
    return fetched_ddo


def run_request_get_data(client_method, url, data=None):
    _response = run_request(client_method, url, data)
    print(f'response: {_response}')
    if _response and _response.data:
        return json.loads(_response.data.decode('utf-8'))

    return None


def run_request(client_method, url, data=None):
    if data is None:
        _response = client_method(url, content_type='application/json')
    else:
        _response = client_method(
            url, data=json.dumps(data), content_type='application/json'
        )

    return _response

def publishDDO(did,flags,data,account):
    print(f'publishDDO {did} with flags: {flags} from {account.address}')
    did = prepare_did(did)
    print('*****************************************************************************\r\n')
    print(did)
    print('*****************************************************************************\r\n')
    transaction = events_contract.functions.create(did,flags,data).buildTransaction()
    transaction.update({ 'gasPrice' : 0 })
    transaction.update({ 'nonce' : web3.eth.getTransactionCount(account.address) })
    signed_tx = web3.eth.account.signTransaction(transaction, account.privateKey)
    txn_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    txn_receipt = web3.eth.waitForTransactionReceipt(txn_hash)
    return(txn_receipt)

def updateDDO(did,flags,data,account):
    print(f'updateDDO {did} with flags: {flags} from {account.address}')
    did = prepare_did(did)
    print('*****************************************************************************\r\n')
    print(did)
    print('*****************************************************************************\r\n')
    web3.eth.defaultAccount = account.address
    txn_hash = events_contract.functions.update(did, flags, data).transact()
    txn_receipt = web3.eth.waitForTransactionReceipt(txn_hash)
    return txn_receipt

def transferOwnership(did,new_owner,account):
    print(f'transferOwnership {did} to {new_owner}')
    did = prepare_did(did)
    transaction = events_contract.functions.transferOwnership(did,new_owner).buildTransaction()
    transaction.update({ 'gasPrice' : 0 })
    transaction.update({ 'nonce' : web3.eth.getTransactionCount(account.address) })
    signed_tx = web3.eth.account.signTransaction(transaction, account.privateKey)
    txn_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    txn_receipt = web3.eth.waitForTransactionReceipt(txn_hash)
    return(txn_receipt)

def prepare_did(text):
    prefix = 'did:op:'
    if text.startswith(prefix):
        text=text[len(prefix):]
    #return bytes.fromhex(text)
    return text
    

def test_publish_and_update_ddo(client,base_ddo_url):
    flags = 0
    ddo_event_sample['publicKey'][0]['owner']=account1.address
    ddo_event_sample['random'] = str(uuid.uuid4())
    ddo_event_sample['id']=new_did(str(uuid.uuid4()))
    did = ddo_event_sample['id']
    ddo_string=json.dumps(ddo_event_sample)
    data = Web3.toBytes(text=ddo_string)
    publishDDO(did,bytes([flags]),data,account1)    
    time.sleep(10)
    # published_ddo = get_ddo(client,base_ddo_url,did)
    #
    # assert published_ddo['id'] == did
    # print(f'Published {published_ddo}')
    ddo_event_sample['service'][0]['attributes']['main']['name']='Updated ddo by event'
    ddo_string=json.dumps(ddo_event_sample)
    data = Web3.toBytes(text=ddo_string)
    updateDDO(did,bytes([flags]),data,account1)
    time.sleep(15)
    published_ddo = get_ddo(client,base_ddo_url,did)
    assert published_ddo['id'] == did
    assert published_ddo['service'][0]['attributes']['main']['name'] == 'Updated ddo by event'

def test_publish_and_update_ddo_with_lzma(client,base_ddo_url):
    flags = 0
    ddo_event_sample['publicKey'][0]['owner']=account1.address
    ddo_event_sample['random'] = str(uuid.uuid4())
    ddo_event_sample['id']=new_did(str(uuid.uuid4()))
    did = ddo_event_sample['id']
    ddo_string=json.dumps(ddo_event_sample)
    data = Lzma.compress(Web3.toBytes(text=ddo_string))
    #mark bit 1
    flags = flags | 1
    publishDDO(did,bytes([flags]),data,account1)    
    # time.sleep(10)
    published_ddo = get_ddo(client,base_ddo_url,did)
    assert published_ddo['id'] == did    

    ddo_event_sample['service'][0]['attributes']['main']['name']='Updated ddo by event'
    ddo_string=json.dumps(ddo_event_sample)
    data = Lzma.compress(Web3.toBytes(text=ddo_string))
    updateDDO(did,bytes([flags]),data,account1)
    # time.sleep(15)
    published_ddo = get_ddo(client,base_ddo_url,did)
    assert published_ddo['id'] == did
    assert published_ddo['service'][0]['attributes']['main']['name'] == 'Updated ddo by event'


def test_publish_and_update_ddo_with_lzma_and_ecies(client,base_ddo_url):
    ddo_event_sample['publicKey'][0]['owner']=account1.address
    ddo_event_sample['random'] = str(uuid.uuid4())
    ddo_event_sample['id']=new_did(str(uuid.uuid4()))
    flags = 0
    did = ddo_event_sample['id']
    ddo_string=json.dumps(ddo_event_sample)
    
    #compression - bit 1
    flags = flags | 1
    data = Lzma.compress(Web3.toBytes(text=ddo_string))
    
    #ecies encrypt - bit 2
    flags = flags | 2
    key = eth_keys.KeyAPI.PrivateKey(account1.privateKey)
    data = ecies.encrypt(key.public_key.to_hex(), data)
    publishDDO(did,bytes([flags]),data,account1)    
    # time.sleep(10)
    # published_ddo = get_ddo(client,base_ddo_url,did)
    # assert published_ddo['id'] == did
    ddo_event_sample['service'][0]['attributes']['main']['name']='Updated ddo by event'
    ddo_string=json.dumps(ddo_event_sample)
    data = Lzma.compress(Web3.toBytes(text=ddo_string))
    data = ecies.encrypt(key.public_key.to_hex(), data)
    updateDDO(did,bytes([flags]),data,account1)
    # time.sleep(15)
    # published_ddo = get_ddo(client,base_ddo_url,did)
    # assert published_ddo['id'] == did
    # assert published_ddo['service'][0]['attributes']['main']['name'] == 'Updated ddo by event'

def test_publish_and_transfer_ownership(client,base_ddo_url):
    flags = 0
    ddo_event_sample['publicKey'][0]['owner']=account1.address
    ddo_event_sample['random'] = str(uuid.uuid4())
    ddo_event_sample['id']=new_did(str(uuid.uuid4()))
    did = ddo_event_sample['id']
    ddo_string=json.dumps(ddo_event_sample)
    data = Web3.toBytes(text=ddo_string)
    publishDDO(did,bytes([flags]),data,account1)    
    # time.sleep(10)
    published_ddo = get_ddo(client,base_ddo_url,did)
    assert published_ddo['id'] == did    
    transferOwnership(did,account2.address,account1)
    # time.sleep(15)
    published_ddo = get_ddo(client,base_ddo_url,did)
    assert published_ddo['id'] == did
    assert published_ddo['publicKey'][0]['owner'] == account2.address


