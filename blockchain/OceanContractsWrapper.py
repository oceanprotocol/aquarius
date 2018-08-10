import os,sys
import json
import time, site
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract
from blockchain.constants import OceanContracts
from provider_backend.config_parser import load_config_section
from provider_backend.myapp import app
from provider_backend.constants import ConfigSections
from threading import Thread
from collections import namedtuple
import asyncio

Signature = namedtuple('Signature', ('v', 'r', 's'))

def get_contracts_path(config):
    try:
        if 'contracts.folder' in config:
            return config['contracts.folder']
        elif os.getenv('VIRTUAL_ENV') is not None:
            return "%s/contracts" % (os.getenv('VIRTUAL_ENV'))
        else:
            return "%s/contracts" % site.getsitepackages()[0]
    except Exception as e:
        return e


class OceanContractsWrapper(object):

    def __init__(self, host=None, port=None, account=None):

        # Don't need these in the global scope
        if 'CONFIG_FILE' in os.environ and os.environ['CONFIG_FILE']:
            app.config['CONFIG_FILE'] = os.environ['CONFIG_FILE']
        else:
            print('A config file must be set in the environment variable "CONFIG_FILE".')
            sys.exit(1)
        config_file = app.config['CONFIG_FILE']
        config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)

        self.host = config['keeper.host'] if 'keeper.host' in config else host

        self.port = config['keeper.port'] if 'keeper.port' in config else port
        self.web3 = OceanContractsWrapper.connect_web3(self.host, self.port)
        self.account = self.web3.eth.accounts[0] if account is None else account
        self.contracts_abis_path = get_contracts_path(config)

        self.contracts = {}
        self.default_contract_address_map = {
            OceanContracts.OMKT: config['market.address'],
            OceanContracts.OACL: config['auth.address'],
            OceanContracts.OTKN: config['token.address']
        }
        # self.encoding_key_pair = generate_encoding_pair()
        # self.cache = SimpleCache()
        # self.keeper_network_id = str(config.get('keeper.networkid', '')).strip()
        # self.api_url = api_url
        # print('OceanContractsWrapper: got api url = "%s"' % self.api_url)

    def init_contracts(self, contracts_folder=None, contracts_addresses=None):
        contracts_abis_path = contracts_folder if contracts_folder else self.contracts_abis_path
        contract_address_map = contracts_addresses if contracts_addresses else self.default_contract_address_map
        for contract_name, address in contract_address_map.items():
            contract_abi_file = os.path.join(contracts_abis_path, contract_name + '.json')
            self.contracts[contract_name] = self.get_contract_instances(contract_abi_file, address)

    @staticmethod
    def connect_web3(host, port='8545'):
        # TODO Resolve http and https
        return Web3(HTTPProvider("%s:%s" % (host, port)))

    def get_contract_instances(self, contract_file, contract_address):
        with open(contract_file, 'r') as abi_definition:
            abi = json.load(abi_definition)
            if not contract_address and self.keeper_network_id and 'networks' in abi:
                deployed_networks = abi['networks']
                if self.keeper_network_id in deployed_networks:
                    contract_address = deployed_networks[self.keeper_network_id]['address']
                    print('Extracted %s contract address ' % contract_file, contract_address)

            concise_cont = self.web3.eth.contract(
                address=self.web3.toChecksumAddress(contract_address),
                abi=abi['abi'],
                ContractFactoryClass=ConciseContract)
            contract = self.web3.eth.contract(
                address=self.web3.toChecksumAddress(contract_address),
                abi=abi['abi'])
            return concise_cont, contract

    def get_tx_receipt(self, tx_hash):
        self.web3.eth.waitForTransactionReceipt(tx_hash)
        return self.web3.eth.getTransactionReceipt(tx_hash)

    def watch_event(self, contract_name, event_name, callback, interval, fromBlock=0, toBlock='latest', filters=None, ):
        event_filter = self.install_filter(
            contract_name, event_name, fromBlock, toBlock, filters
        )
        event_filter.poll_interval = interval
        Thread(
            target=self.watcher,
            args=(event_filter, callback),
            daemon=True,
        ).start()
        return event_filter

    def watcher(self, event_filter, callback):
        while True:
            try:
                events = event_filter.get_all_entries()
            except ValueError as err:
                # ignore error, but log it
                print('Got error grabbing keeper events: ', str(err))
                events = []

            for event in events:
                callback(event)
                # time.sleep(0.1)

            # always take a rest
            time.sleep(0.1)

    def install_filter(self, contract_name, event_name, fromBlock=0, toBlock='latest', filters=None):
        contract_instance = self.contracts[contract_name][1]
        event = getattr(contract_instance.events, event_name)
        event_filter = event.createFilter(
            fromBlock=fromBlock, toBlock=toBlock, argument_filters=filters
        )
        return event_filter

    def to_32byte_hex(self, val):
        return self.web3.toBytes(val).rjust(32, b'\0')

    def split_signature(self, signature):
        v = self.web3.toInt(signature[-1])
        r = self.to_32byte_hex(int.from_bytes(signature[:32], 'big'))
        s = self.to_32byte_hex(int.from_bytes(signature[32:64], 'big'))
        if v != 27 and v != 28:
            v = 27 + v % 2
        return Signature(v, r, s)

    # def commit_access_request(self, event):
    #     contract_instance = self.contracts[OceanContracts.OACL][0]
    #     try:
    #         resource = self.dao.get(self.web3.toHex(event['args']['_resourceId']))
    #         _cache = dict()
    #         _cache['access_request'] = event['args']
    #         _cache['resource_metadata'] = resource
    #         gas_amount = 4000000
    #         commit_access_request = contract_instance.commitAccessRequest(event['args']['_id'], True,
    #                                                                       event['args']['_timeout'], 'discovery',
    #                                                                       'read', 'slaLink',
    #                                                                       'slaType',
    #                                                                       transact={
    #                                                                           'from': event['args']['_provider'],
    #                                                                           'gas': gas_amount
    #                                                                       }
    #         )
    #         print('Provider has committed the order, transactionId is: %s' % commit_access_request)
    #         _cache['consent_hash'] = self.web3.toHex(commit_access_request)
    #         self.cache.add(event['args']['_id'], _cache)
    #         return commit_access_request
    #     except Exception as e:
    #         # Don't need to cancel request, in case of error we can do a retry mechanism. So far most failures are due
    #         # to issues with gas amount. Also if this call throws an error, it will mess up the event watcher.
    #         # contract_instance.cancelAccessRequest(event['args']['_id'], transact={
    #         #     'from': event['args']['_provider']})
    #         print('There is no resource with this id registered in Oceandb.')
    #         return e
    #
    # def publish_encrypted_token(self, event):
    #     contract_instance = self.contracts[OceanContracts.OACL][0]
    #     try:
    #         c = self.cache.get(event['args']['_paymentId'])
    #         iat = time.time()
    #         # TODO Validate that all the values are good.
    #         jwt = encode({
    #             "iss": c['access_request']['_provider'],
    #             "sub": c['resource_metadata']['data']['data']['metadata']['name'],  # Resource Name
    #             "iat": iat,
    #             "exp": iat + event['args']['_expire'],
    #             "consumer_pubkey": "Consumer Public Key",  # Consumer Public Key
    #             "temp_pubkey": c['access_request']['_pubKey'],
    #             "request_id": self.web3.toHex(event['args']['_paymentId']),  # Request Identifier
    #             "consent_hash": c['consent_hash'],  # Consent Hash
    #             "resource_id": self.web3.toHex(c['resource_metadata']['assetId']),  # Resource Identifier
    #             # Timeout coming from OceanAuth contract, specified by provider in the commitment consent.
    #             "timeout": event['args']['_expire'],
    #             "response_type": "Signed_URL",
    #             "resource_server_plugin": "Azure",
    #             "service_endpoint": "%s/metadata/consume" % self.api_url,
    #             "nonce": token_hex(32),
    #         }, self.encoding_key_pair.private_key)
    #         public_key = c['access_request']['_pubKey']
    #         enc_jwt = enc(jwt, public_key)
    #         # print('encrypting token:',
    #         #       '\nencoded jwt: ', jwt,
    #         #       '\npublicKey: ', public_key,
    #         # )
    #         self.cache.delete(event['args']['_paymentId'])
    #         print("Delivering encrypted JWT (access token): %s" % enc_jwt.hex())
    #         deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
    #                                                                    enc_jwt,
    #                                                                    transact={'from': event['args']['_receiver'],
    #                                                                              'gas': 4000000})
    #         print('Provider has sent the access token, transactionId is: %s' % deliver_acces_token)
    #         return deliver_acces_token
    #     except Exception as e:
    #         return e
