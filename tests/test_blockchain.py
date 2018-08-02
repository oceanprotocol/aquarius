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


def test_commit_access_requested():
    print("Starting test_commit_access_requested")
    resource_id = market_concise.generateId('resource', transact={'from': ocean.web3.eth.accounts[0]})
    print("recource_id: %s" % resource_id)
    resource_price = 10

    pubprivkey = generate_encryption_keys()
    pubkey = pubprivkey.public_key
    privkey = pubprivkey.private_key

    market_concise.requestTokens(2000, transact={'from': ocean.web3.eth.accounts[0]})
    market_concise.requestTokens(2000, transact={'from': ocean.web3.eth.accounts[1]})
    print('buyer balance = ', token.balanceOf(ocean.web3.eth.accounts[1]))
    print('seller balance = ', token.balanceOf(ocean.web3.eth.accounts[0]))

    filter_access_consent = ocean.watch_event(OceanContracts.OACL, 'AccessConsentRequested',
                                              ocean.commit_access_request, 500,
                                              fromBlock='latest', filters={"address": ocean.web3.eth.accounts[0]})
    filter_payment = ocean.watch_event(OceanContracts.OMKT, 'PaymentReceived', ocean.publish_encrypted_token, 500,
                                       fromBlock='latest', filters={"address": ocean.web3.eth.accounts[0]})

    # 1. Provider register an asset
    market_concise.register(resource_id,
                            resource_price,
                            transact={'from': ocean.web3.eth.accounts[0]})
    # 2. Consumer initiate an access request
    req = acl_concise.initiateAccessRequest(resource_id,
                                            ocean.web3.eth.accounts[0],
                                            pubkey,
                                            9999999999,
                                            transact={'from': ocean.web3.eth.accounts[1]})
    receipt = ocean.get_tx_receipt(req)
    send_event = acl.events.AccessConsentRequested().processReceipt(receipt)
    request_id = send_event[0]['args']['_id']
    assert send_event[0] == filter_access_consent.get_new_entries()[0]

    # 3. Provider commit the request in commit_access_request

    # 4. consumer make payment after approve spend token
    token.approve(ocean.web3.toChecksumAddress(market_concise.address),
                  resource_price,
                  transact={'from': ocean.web3.eth.accounts[1]})

    send_payment = market_concise.sendPayment(request_id,
                                              ocean.web3.eth.accounts[0],
                                              resource_price,
                                              9999999999,
                                              transact={'from': ocean.web3.eth.accounts[1]})

    print('buyer balance = ', token.balanceOf(ocean.web3.eth.accounts[1]))
    print('seller balance = ', token.balanceOf(ocean.web3.eth.accounts[0]))

    # Verify consent has been emited
    assert acl_concise.verifyCommitted(request_id, 1)

    assert filter_payment.get_new_entries()[0]['transactionHash'] == send_payment

    assert acl_concise.getTempPubKey(request_id) == pubkey

    on_chain_enc_token = acl_concise.getEncryptedAccessToken(request_id, call={'from': ocean.web3.eth.accounts[1]})

    print("jwt: %s" % decode(dec(on_chain_enc_token, privkey), ocean.encoding_key_pair.public_key))

    assert pubkey == decode(dec(on_chain_enc_token, privkey), ocean.encoding_key_pair.public_key)['temp_pubkey']

    signature = ocean.web3.eth.sign(ocean.web3.eth.accounts[1], data=on_chain_enc_token)

    fixed_msg = defunct_hash_message(hexstr=ocean.web3.toHex(on_chain_enc_token))
    # fixed_msg_sha = ocean.web3.sha3(fixed_msg)

    sig = ocean.split_signature(signature)

    assert acl_concise.isSigned(ocean.web3.eth.accounts[1],
                                ocean.web3.toHex(fixed_msg),
                                sig.v,
                                sig.r,
                                sig.s,
                                call={'from': ocean.web3.eth.accounts[0]})

    assert acl_concise.verifyAccessTokenDelivery(request_id,
                                                 ocean.web3.eth.accounts[1],
                                                 ocean.web3.toHex(fixed_msg),
                                                 sig.v,
                                                 sig.r,
                                                 sig.s,
                                                 call={'from': ocean.web3.eth.accounts[0]})
