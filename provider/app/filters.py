import traceback
from secrets import token_hex
from acl.acl import enc, encode, generate_encoding_pair
import time
from blockchain.constants import OceanContracts
from provider.app.dao import Dao
from werkzeug.contrib.cache import SimpleCache


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
            res_id = self.web3.toHex(event['args']['_resourceId'])
            request_id = self.web3.toHex(event['args']['_id'])
            # consumer = event['args']['_consumer']
            # provider = event['args']['_provider']

            # check keeper for the status of this access request, if already committed then it should be ignored.
            committed = contract_instance.statusOfAccessRequest(request_id) == 1
            if committed:
                print('got access request event, but it is already committed, ignoring... ', request_id)
                return

            # print('process access request: ',
            #       '\nresourceId: ', res_id,
            #       '\nrequestId: ', request_id,
            #       '\nconsumer: ', consumer,
            #       '\nprovider: ', provider)

            try:
                resource = self.dao.get(res_id)
            except Exception:
                # print('res id: ', res_id)
                return

            _cache = dict()
            _cache['access_request'] = event['args']
            _cache['resource_metadata'] = resource
            print('cached resource: ', res_id, resource)
            gas_amount = 1000000
            commit_access_request_tx = contract_instance.commitAccessRequest(event['args']['_id'], True,
                                                                             event['args']['_timeout'], 'discovery',
                                                                             'read', 'slaLink',
                                                                             'slaType',
                                                                             transact={
                                                                                 'from': event['args']['_provider'],
                                                                                 'gas': gas_amount}
                                                                             )
            # print('Provider has committed the order, res_id, request_id: ', res_id, request_id)
            _cache['consent_hash'] = self.web3.toHex(commit_access_request_tx)
            self.cache.add(request_id, _cache)
            return commit_access_request_tx
        except Exception as e:
            # Don't need to cancel request, in case of error we can do a retry mechanism. So far most failures are due
            # to issues with gas amount. Also if this call throws an error, it will mess up the event watcher.
            # contract_instance.cancelAccessRequest(event['args']['_id'], transact={
            #     'from': event['args']['_provider']})
            print('There is no resource with this id registered in Oceandb.', traceback.print_exc())
            return e

    def publish_encrypted_token(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            request_id = self.web3.toHex(event['args']['_paymentId'])

            # check keeper for the status of this access request, if the status is not committed should be ignored.
            committed = contract_instance.statusOfAccessRequest(request_id) != 1
            if committed:
                print('got payment received event, but the encrypted token has been already publish, ignoring... ',
                      request_id)
                return

            print('payment id: ', request_id, self.cache._cache)
            c = self.cache.get(request_id)
            asset_id = c['resource_metadata']['data']['data']['assetId']
            iat = time.time()
            # TODO Validate that all the values are good.
            plain_jwt = {
                "iss": c['access_request']['_provider'],
                "sub": c['resource_metadata']['data']['data']['metadata']['name'],  # Resource Name
                "iat": iat,
                "exp": iat + event['args']['_expire'],
                "consumer_pubkey": "Consumer Public Key",  # Consumer Public Key
                "temp_pubkey": c['access_request']['_pubKey'],
                "request_id": request_id,  # Request Identifier
                "consent_hash": c['consent_hash'],  # Consent Hash
                "resource_id": asset_id,  # Resource Identifier
                # Timeout coming from OceanAuth contract, specified by provider in the commitment consent.
                "timeout": event['args']['_expire'],
                "response_type": "Signed_URL",
                "resource_server_plugin": "Azure",
                "service_endpoint": "%s/metadata/consume" % self.api_url,
                "nonce": token_hex(32),
            }
            jwt = encode(plain_jwt, self.encoding_key_pair.private_key)
            public_key = c['access_request']['_pubKey']
            enc_jwt = enc(jwt, public_key)
            # print('publishing jwt: ', plain_jwt)
            # print('encrypting token:',
            #       '\nencoded jwt: ', jwt,
            #       '\npublicKey: ', public_key,
            # )
            # self.cache.delete(event['args']['_paymentId'])
            # print("Delivering encrypted JWT (access token): %s" % enc_jwt.hex())
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       enc_jwt,
                                                                       transact={'from': event['args']['_receiver'],
                                                                                 'gas': 4000000})
            # print('Provider has sent the access token, transactionId is: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            print('error processing payment event (trying to publish JWT)', str(e), traceback.print_exc())
            return e
