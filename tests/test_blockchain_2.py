import time

from provider_backend.blockchain.constants import OceanContracts
from provider_backend.blockchain.OceanContractsWrapper import OceanContractsWrapper
from provider_backend.acl.acl import generate_encryption_keys, decode, encode, generate_encoding_pair, dec
from eth_account.messages import defunct_hash_message

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


def test_commit_access_requested():
    expire_seconds = 9999999999
    consumer_account = ocean.web3.eth.accounts[1]
    provider_account = ocean.web3.eth.accounts[0]
    print("Starting test_commit_access_requested")
    print("buyer: %s" % consumer_account)
    print("seller: %s" % provider_account)

    resource_id = market_concise.generateId('resource', transact={'from': provider_account})
    print("recource_id: %s" % resource_id)
    resource_price = 10

    pubprivkey = generate_encryption_keys()
    pubkey = pubprivkey.public_key
    privkey = pubprivkey.private_key

    market_concise.requestTokens(2000, transact={'from': provider_account})
    market_concise.requestTokens(2000, transact={'from': consumer_account})

    filter_access_consent = ocean.watch_event(OceanContracts.OACL, 'AccessConsentRequested',
                                              ocean.commit_access_request, 250,
                                              fromBlock='latest', filters={"address": provider_account})
    filter_payment = ocean.watch_event(OceanContracts.OMKT, 'PaymentReceived', ocean.publish_encrypted_token, 2500,
                                       fromBlock='latest', filters={"address": provider_account})

    # 1. Provider register an asset
    market_concise.register(resource_id,
                            resource_price,
                            transact={'from': provider_account})
    # 2. Consumer initiate an access request
    expiry = int(time.time() + expire_seconds)
    req = acl_concise.initiateAccessRequest(resource_id,
                                            provider_account,
                                            pubkey,
                                            expiry,
                                            transact={'from': consumer_account})
    receipt = ocean.get_tx_receipt(req)
    send_event = acl.events.AccessConsentRequested().processReceipt(receipt)
    request_id = send_event[0]['args']['_id']

    events = get_events(filter_access_consent)

    assert send_event[0] in events
    assert acl_concise.verifyCommitted(request_id, 0) or acl_concise.verifyCommitted(request_id, 1)

    filter_token_published = ocean.watch_event(OceanContracts.OACL, 'EncryptedTokenPublished', process_enc_token, 250,
                                       fromBlock='latest')#, filters={"id": request_id})

    # 3. Provider commit the request in commit_access_request

    # Verify consent has been emited
    i = 0
    while acl_concise.verifyCommitted(request_id, 1) is False and i < 100:
        i += 1
        time.sleep(0.1)

    assert acl_concise.verifyCommitted(request_id, 1)

    # 4. consumer make payment after approve spend token
    token.approve(ocean.web3.toChecksumAddress(market_concise.address),
                  resource_price,
                  transact={'from': consumer_account})

    buyer_balance_start = token.balanceOf(consumer_account)
    seller_balance_start = token.balanceOf(provider_account)
    print('starting buyer balance = ', buyer_balance_start)
    print('starting seller balance = ', seller_balance_start)

    send_payment = market_concise.sendPayment(request_id,
                                              provider_account,
                                              resource_price,
                                              expiry,
                                              transact={'from': consumer_account, 'gas': 400000})

    print('buyer balance = ', token.balanceOf(consumer_account))
    print('seller balance = ', token.balanceOf(provider_account))

    tx_hashes = set()
    events = get_events(filter_payment)
    for ev in events:
        tx_hashes.add(ev['transactionHash'])

    assert events
    assert send_payment in tx_hashes

    assert acl_concise.getTempPubKey(request_id, call={"from": provider_account}) == pubkey

    events = get_events(filter_token_published)
    assert events
    assert events[0].args['_id'] == request_id
    on_chain_enc_token = events[0].args["_encryptedAccessToken"]
    on_chain_enc_token2 = acl_concise.getEncryptedAccessToken(request_id, call={'from': consumer_account})

    decrypted_token = dec(on_chain_enc_token, privkey)
    pub_key = ocean.encoding_key_pair.public_key
    access_token = decode(decrypted_token, pub_key)

    assert pubkey == access_token['temp_pubkey']
    signature = ocean.web3.eth.sign(consumer_account, data=on_chain_enc_token)

    fixed_msg = defunct_hash_message(hexstr=ocean.web3.toHex(on_chain_enc_token))

    sig = ocean.split_signature2(signature)

    assert acl_concise.isSigned(consumer_account,
                                ocean.web3.toHex(fixed_msg),
                                sig.v,
                                sig.r,
                                sig.s,
                                call={'from': provider_account})

    verify = acl_concise.verifyAccessTokenDelivery(request_id,
                                                 consumer_account,
                                                 ocean.web3.toHex(fixed_msg),
                                                 sig.v,
                                                 sig.r,
                                                 sig.s,
                                                 transact={'from': provider_account})

    receipt_payment_release = ocean.get_tx_receipt(verify)
    market.events.PaymentReleased().processReceipt(receipt_payment_release)
    assert acl_concise.verifyCommitted(request_id, 2)

    buyer_balance = token.balanceOf(consumer_account)
    seller_balance = token.balanceOf(provider_account)
    print('end: buyer balance -- current %s, starting %s, diff %s' % (buyer_balance, buyer_balance_start, (buyer_balance - buyer_balance_start)))
    print('end: seller balance -- current %s, starting %s, diff %s' % (seller_balance, seller_balance_start, (seller_balance - seller_balance_start)))
    assert token.balanceOf(consumer_account) == buyer_balance_start - resource_price
    assert token.balanceOf(provider_account) == seller_balance_start + resource_price
    print('All good \/')