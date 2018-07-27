from provider_backend.blockchain.ocean_contracts import OceanContracts
from provider_backend.acl.acl import generate_encription_keys,decode,encode,generate_encoding_pair


ocean = OceanContracts()
ocean.init_contracts()

acl_concise = ocean.concise_contracts['Auth.json']
acl = ocean.contracts['Auth.json']
market_concise = ocean.concise_contracts['Market.json']
market = ocean.contracts['Market.json']
token = ocean.concise_contracts['OceanToken.json']


def test_version_contracts():
    assert '0.3' == market_concise.version()


def test_commit_access_requested():
    print("Starting test_commit_access_requested")
    resource_id = market_concise.generateStr2Id('resouce', transact={'from': ocean.web3.eth.accounts[0]})
    print("recource_id: %s" % resource_id)
    resource_price = 10

    # pubprivkey = generate_encription_keys()
    pubprivkey = generate_encoding_pair()
    pubkey = pubprivkey.public_key
    privkey = pubprivkey.private_key

    market_concise.requestTokens(2000, transact={'from': ocean.web3.eth.accounts[0]})
    market_concise.requestTokens(2000, transact={'from': ocean.web3.eth.accounts[1]})
    print('buyer balance = ', token.balanceOf(ocean.web3.eth.accounts[1]))
    print('seller balance = ', token.balanceOf(ocean.web3.eth.accounts[0]))


    filter_access_consent = ocean.watch_event('Auth', 'RequestAccessConsent', ocean.commit_access_request, 500,
                                              fromBlock='latest', filters={"address": ocean.web3.eth.accounts[0]})
    filter_payment = ocean.watch_event('Market', 'PaymentReceived', ocean.publish_encrypted_token, 500,
                                       fromBlock='latest', filters={"address": ocean.web3.eth.accounts[0]})

    # filter = ocean.watch_event(ocean.commit_access_request, 500, ocean.web3.eth.accounts[0])
    # filter = ocean._request_access_consent_filter(ocean.web3.eth.accounts[0])

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
    send_event = acl.events.RequestAccessConsent().processReceipt(receipt)
    access_id=send_event[0]['args']['_id']
    assert send_event[0] == filter_access_consent.get_all_entries()[0]

    # 3. Provider commit the request in commit_access_request

    # 4. consumer make payment after approve spend token
    token.approve(ocean.web3.toChecksumAddress(market_concise.address),
                  resource_price,
                  transact={'from': ocean.web3.eth.accounts[1]})

    send_payment = market_concise.sendPayment(access_id,
                               ocean.web3.eth.accounts[0],
                               resource_price,
                               9999999999,
                               transact={'from': ocean.web3.eth.accounts[1]})


    print('buyer balance = ', token.balanceOf(ocean.web3.eth.accounts[1]))
    print('seller balance = ', token.balanceOf(ocean.web3.eth.accounts[0]))

    # Verify consent has been emited
    assert acl_concise.verifyCommitted(access_id,1) == True



    # assert filter_payment.get_all_entries()[0]['transactionHash'] == send_payment

    assert acl_concise.getTempPubKey(access_id) == pubkey.decode('utf-8')


    jwt = acl_concise.getEncJWT(access_id, call={'from': ocean.web3.eth.accounts[1]})


    print("jwt: %s" % jwt)
    print("jwt: %s" % decode(jwt, privkey))


    print("Test finished")

    # acl.commitAccessRequest(accessId, True, 9999999999, 'discovery', 'read', 'slaLink', 'slaType')
