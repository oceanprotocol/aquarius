import time

from blockchain.constants import OceanContracts
from blockchain.OceanContractsWrapper import OceanContractsWrapper
from acl.acl import generate_encryption_keys, decode, dec
from eth_account.messages import defunct_hash_message
import json
from provider_backend.constants import BaseURLs
from threading import Thread

ocean = OceanContractsWrapper()
ocean.init_contracts()

acl_concise = ocean.contracts[OceanContracts.OCEAN_ACL_CONTRACT][0]
acl = ocean.contracts[OceanContracts.OCEAN_ACL_CONTRACT][1]
market_concise = ocean.contracts[OceanContracts.OCEAN_MARKET_CONTRACT][0]
market = ocean.contracts[OceanContracts.OCEAN_MARKET_CONTRACT][1]
token = ocean.contracts[OceanContracts.OCEAN_TOKEN_CONTRACT][0]


def get_events(event_filter, max_iterations=100, pause_duration=0.1):
    events = event_filter.get_new_entries()
    i = 0
    while not events and i < max_iterations:
        i += 1
        time.sleep(pause_duration)
        events = event_filter.get_new_entries()

    if not events:
        print('no events found in %s events filter.' % str(event_filter))
    return events


def process_enc_token(event):
    # should get accessId and encryptedAccessToken in the event
    print("token published event: %s" % event)

def consume(resource):
    expire_seconds = 9999999999
    consumer_account = ocean.web3.eth.accounts[1]
    provider_account = ocean.web3.eth.accounts[0]
    resource_id = ocean.web3.toBytes(hexstr=resource)
    resource_price = 10

    pubprivkey = generate_encryption_keys()
    pubkey = pubprivkey.public_key
    privkey = pubprivkey.private_key
    market_concise.requestTokens(2000, transact={'from': provider_account})
    market_concise.requestTokens(2000, transact={'from': consumer_account})
    expiry = int(time.time() + expire_seconds)
    req = acl_concise.initiateAccessRequest(resource_id,
                                            provider_account,
                                            pubkey,
                                            expiry,
                                            transact={'from': consumer_account})
    receipt = ocean.get_tx_receipt(req)
    send_event = acl.events.AccessConsentRequested().processReceipt(receipt)
    request_id = send_event[0]['args']['_id']
    i = 0
    while acl_concise.verifyCommitted(request_id, 1) is False and i < 100:
        i += 1
        time.sleep(0.1)

    assert acl_concise.verifyCommitted(request_id, 1)
    token.approve(ocean.web3.toChecksumAddress(market_concise.address),
                  resource_price,
                  transact={'from': consumer_account})
    send_payment = market_concise.sendPayment(request_id,
                                              provider_account,
                                              resource_price,
                                              expiry,
                                              transact={'from': consumer_account, 'gas': 400000})
    assert acl_concise.getTempPubKey(request_id, call={"from": provider_account}) == pubkey


def test_commit_access_requested():
    Thread(consume('0xfc3668944977b0902e8880de6b340b9022eeb1858256b5b96da2372d63fa01aa')).start()
    Thread(consume('0x1298371984723941')).start()