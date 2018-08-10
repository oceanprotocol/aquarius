from secrets import token_hex
from acl.acl import enc, encode, generate_encoding_pair
import time
from blockchain.constants import OceanContracts
from provider_backend.app.dao import Dao
from werkzeug.contrib.cache import SimpleCache
from provider_backend.constants import BaseURLs


class Filters(object):

    def __init__(self, ocean_contracts_wrapper, config_file, api_url):
        self.contracts = ocean_contracts_wrapper.contracts
        self.web3 = ocean_contracts_wrapper.web3
        self.dao = Dao(config_file)
        self.cache = SimpleCache()
        self.encoding_key_pair = generate_encoding_pair()
        self.api_url = api_url
        print('Keeper filters: got api url = "%s"' % self.api_url)

    def commit_access_request(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            resource = self.dao.get(self.web3.toHex(event['args']['_resourceId']))
            _cache = dict()
            _cache['access_request'] = event['args']
            _cache['resource_metadata'] = resource
            gas_amount = 4000000
            commit_access_request_tx = contract_instance.commitAccessRequest(event['args']['_id'], True,
                                                                          event['args']['_timeout'], 'discovery',
                                                                          'read', 'slaLink',
                                                                          'slaType',
                                                                          transact={
                                                                              'from': event['args']['_provider'],
                                                                              'gas': gas_amount
                                                                          }
            )
            print('Provider has committed the order, transactionId is: %s' % commit_access_request_tx)
            _cache['consent_hash'] = self.web3.toHex(commit_access_request_tx)
            self.cache.add(event['args']['_id'], _cache)
            return commit_access_request_tx
        except Exception as e:
            # Don't need to cancel request, in case of error we can do a retry mechanism. So far most failures are due
            # to issues with gas amount. Also if this call throws an error, it will mess up the event watcher.
            # contract_instance.cancelAccessRequest(event['args']['_id'], transact={
            #     'from': event['args']['_provider']})
            print('There is no resource with this id registered in Oceandb.')
            return e

    def publish_encrypted_token(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            c = self.cache.get(event['args']['_paymentId'])
            iat = time.time()
            # TODO Validate that all the values are good.
            jwt = encode({
                "iss": c['access_request']['_provider'],
                "sub": c['resource_metadata']['data']['data']['metadata']['name'],  # Resource Name
                "iat": iat,
                "exp": iat + event['args']['_expire'],
                "consumer_pubkey": "Consumer Public Key",  # Consumer Public Key
                "temp_pubkey": c['access_request']['_pubKey'],
                "request_id": self.web3.toHex(event['args']['_paymentId']),  # Request Identifier
                "consent_hash": c['consent_hash'],  # Consent Hash
                "resource_id": self.web3.toHex(hexstr=c['resource_metadata']['data']['data']['assetId']),  # Resource Identifier
                # Timeout coming from OceanAuth contract, specified by provider in the commitment consent.
                "timeout": event['args']['_expire'],
                "response_type": "Signed_URL",
                "resource_server_plugin": "Azure",
                "service_endpoint": "%s/metadata/consume" % self.api_url,
                "nonce": token_hex(32),
            }, self.encoding_key_pair.private_key)
            public_key = c['access_request']['_pubKey']
            enc_jwt = enc(jwt, public_key)
            # print('encrypting token:',
            #       '\nencoded jwt: ', jwt,
            #       '\npublicKey: ', public_key,
            # )
            self.cache.delete(event['args']['_paymentId'])
            print("Delivering encrypted JWT (access token): %s" % enc_jwt.hex())
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       enc_jwt,
                                                                       transact={'from': event['args']['_receiver'],
                                                                                 'gas': 4000000})
            print('Provider has sent the access token, transactionId is: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            print("Error creating jwt: %e" % e)
            return e
