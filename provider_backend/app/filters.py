from secrets import token_hex
from acl.acl import enc, encode, generate_encoding_pair
import time
from blockchain.constants import OceanContracts
from provider_backend.app.dao import Dao
from werkzeug.contrib.cache import SimpleCache


class Filters(object):

    def __init__(self, ocean_contracts_wrapper, config_file, api_url=None):
        self.contracts = ocean_contracts_wrapper.contracts
        self.web3 = ocean_contracts_wrapper.web3
        self.dao = Dao(config_file)
        self.cache = SimpleCache()
        self.encoding_key_pair = generate_encoding_pair()
        self.api_url = api_url

    def commit_access_request(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            resource = self.dao.get(self.web3.toHex(event['args']['_resourceId']))
            _cache = dict()
            _cache['access_request'] = event['args']
            _cache['resource_metadata'] = resource
            commit_access_request = contract_instance.commitAccessRequest(event['args']['_id'], True,
                                                                          event['args']['_timeout'], 'discovery',
                                                                          'read', 'slaLink',
                                                                          'slaType',
                                                                          transact={'from': event['args']['_provider']})
            print('Provider has committed the order: %s' % commit_access_request)
            _cache['consent_hash'] = self.web3.toHex(commit_access_request)
            self.cache.add(event['args']['_id'], _cache)
            return commit_access_request
        except Exception as e:
            contract_instance.cancelAccessRequest(event['args']['_id'], transact={
                'from': event['args']['_provider']})
            print('There are not resource with this id register in Oceandb.')
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
                "resource_id": self.web3.toHex(c['access_request']['_id']),  # Resource Identifier
                "timeout": event['args']['_expire'],  # Timeout comming from AUTH contract
                "response_type": "Signed_URL",
                "resource_server_plugin": "Azure",
                "service_endpoint": "%s/consume" % self.api_url,
                "nonce": token_hex(32),
            }, self.encoding_key_pair.private_key)
            encJWT = enc(jwt, c['access_request']['_pubKey'])
            self.cache.delete(event['args']['_paymentId'])
            print("Delivering token jwt: %s" % encJWT)
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       encJWT,
                                                                       transact={'from': event['args']['_receiver']})
            print('Provider has send the jwt: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            return e
