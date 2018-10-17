import traceback
from secrets import token_hex
from squid_py.acl import encrypt, encode, generate_encoding_pair
import time
from provider.app.dao import Dao
from werkzeug.contrib.cache import SimpleCache
import logging


class Filters(object):

    def __init__(self, ocean_contracts_wrapper, config_file, api_url):
        self.contracts = ocean_contracts_wrapper.contracts
        self.web3 = ocean_contracts_wrapper.web3
        self.dao = Dao(config_file)
        self.cache = SimpleCache()
        self.encoding_key_pair = generate_encoding_pair()
        self.api_url = api_url
        logging.info('Keeper filters: got api url = "%s"' % self.api_url)

    def commit_access_request(self, event):
        contract_instance = self.contracts.auth.contract_concise
        try:
            res_id = self.web3.toHex(event['args']['_resourceId'])
            request_id = self.web3.toHex(event['args']['_id'])
            # check keeper for the status of this access request, if already committed then it should be ignored.
            committed = contract_instance.statusOfAccessRequest(request_id) == 1
            if committed:
                logging.info('got access request event, but it is already committed, ignoring... %s' % request_id)
                return
            logging.debug('process access request: '
                          '\nresourceId: %s'
                          '\nrequestId: %s'
                          '\nconsumer: %s'
                          '\nprovider: %s' % (
                              res_id, request_id, event['args']['_consumer'], event['args']['_provider']))
            try:
                resource = self.dao.get(res_id)
            except Exception as e:
                logging.info('res id: %s' % res_id)
                logging.info(str(e))
                return
            _cache = dict()
            _cache['access_request'] = event['args']
            _cache['resource_metadata'] = resource
            logging.debug('cached resource: %s %s' % (res_id, resource))
            gas_amount = 1000000
            commit_access_request_tx = contract_instance.commitAccessRequest(event['args']['_id'], True,
                                                                             event['args']['_timeout'], 'discovery',
                                                                             'read', 'slaLink',
                                                                             'slaType',
                                                                             transact={
                                                                                 'from': event['args']['_provider'],
                                                                                 'gas': gas_amount}
                                                                             )
            logging.debug('Provider has committed the order, res_id, request_id: %s,%s' % (res_id, request_id))
            _cache['consent_hash'] = self.web3.toHex(commit_access_request_tx)
            self.cache.add(request_id, _cache)
            return commit_access_request_tx
        except Exception as e:
            # Don't need to cancel request, in case of error we can do a retry mechanism. So far most failures are due
            # to issues with gas amount. Also if this call throws an error, it will mess up the event watcher.
            # contract_instance.cancelAccessRequest(event['args']['_id'], transact={
            #     'from': event['args']['_provider']})
            logging.error('There is no resource with this id registered in Oceandb.')
            logging.error(traceback.print_exc())
            return e

    def publish_encrypted_token(self, event):
        contract_instance = self.contracts.auth.contract_concise
        try:
            request_id = self.web3.toHex(event['args']['_paymentId'])
            # check keeper for the status of this access request, if the status is not committed should be ignored.
            committed = contract_instance.statusOfAccessRequest(request_id) != 1
            if committed:
                logging.info('got payment received event, but the encrypted token has been already publish,')
                logging.info('ignoring... %s' % request_id)
                return
            logging.debug('payment id: %s' % request_id)
            c = self.cache.get(request_id)
            asset_id = c['resource_metadata']['assetId']
            iat = time.time()
            # TODO Validate that all the values are good.
            plain_jwt = {
                "iss": c['access_request']['_provider'],
                "sub": c['resource_metadata']['base']['name'],  # Resource Name
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
            enc_jwt = encrypt(jwt, public_key)
            self.cache.delete(event['args']['_paymentId'])
            logging.debug("Delivering encrypted JWT (access token): %s" % enc_jwt.hex())
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       enc_jwt,
                                                                       transact={'from': event['args']['_receiver'],
                                                                                 'gas': 4000000})
            logging.debug('Provider has sent the access token, transactionId is: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            logging.error('error processing payment event (trying to publish JWT)')
            logging.error(traceback.print_exc())
            return e
