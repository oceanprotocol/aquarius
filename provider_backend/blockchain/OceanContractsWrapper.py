import os
import json
import requests
import time, site
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

from acl.acl import generate_sasurl
from provider_backend.blockchain.constants import OceanContracts
from provider_backend.config_parser import load_config_section
from provider_backend.myapp import app
from provider_backend.constants import ConfigSections
from provider_backend.acl.acl import enc, dec, encode, generate_encoding_pair
from threading import Thread
from secrets import token_hex

def convert_to_bytes(data):
    return Web3.toBytes(text=data)


def convert_to_string(data):
    return Web3.toHex(data)


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

    def __init__(self, host, port, account=None):

        # Don't need these in the global scope
        config_file = app.config['CONFIG_FILE']
        config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)

        self.host = host
        self.port = port
        self.web3 = OceanContractsWrapper.connect_web3(self.host, self.port)
        self.account = self.web3.eth.accounts[0] if account is None else account
        self.contracts_abis_path = get_contracts_path(config)

        self.contracts = {}
        self.default_contract_address_map = {
            OceanContracts.OMKT: config['market.address'],
            OceanContracts.OACL: config['auth.address'],
            OceanContracts.OTKN: config['token.address']
        }
        self.encoding_key_pair = generate_encoding_pair()

    def init_contracts(self, contracts_folder=None, contracts_addresses=None):
        contracts_abis_path = contracts_folder if contracts_folder else self.contracts_abis_path
        contract_address_map = contracts_addresses if contracts_addresses else self.default_contract_address_map
        for contract_name, address in contract_address_map.items():
            contract_abi_file = os.path.join(contracts_abis_path, contract_name + '.json')
            self.contracts[contract_name] = self.get_contract_instances(contract_abi_file, address)

    @staticmethod
    def connect_web3(host, port='8545'):
        return Web3(HTTPProvider("http://%s:%s" % (host, port)))

    def get_contract_instances(self, contract_file, contract_address):
        with open(contract_file, 'r') as abi_definition:
            abi = json.load(abi_definition)

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
        event_filter.poll_interval = 500
        Thread(
            target=self.watcher,
            args=(event_filter, callback, interval),
            daemon=True,
        ).start()
        return event_filter

    def watcher(self, event_filter, callback, interval):
        while True:
            for event in event_filter.get_all_entries():
                callback(event)
                time.sleep(interval)

    def install_filter(self, contract_name, event_name, fromBlock=0, toBlock='latest', filters=None):
        contract_instance = self.contracts[contract_name][1]
        event = getattr(contract_instance.events, event_name)
        eventFilter = event.createFilter(
            fromBlock=fromBlock, toBlock=toBlock, argument_filters=filters
        )
        return eventFilter

    def commit_access_request(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            # TODO register metadata of the request.
            # requests.post('/api/v1/provider/assets/metadata', data=json.dumps({"publisherId": "0x1",
            #                                                                    "metadata": {
            #                                                                        "name": "name",
            #                                                                        "links": ["link"],
            #                                                                        "size": "size",
            #                                                                        "format": "format",
            #                                                                        "description": "description"
            #                                                                    },
            #                                                                    "assetId": "001",
            #                                                                    "consumerAddress": event['args'][
            #                                                                        '_consumer'],
            #                                                                    "consumerTempPubKey": event['args'][
            #                                                                        '_pubkey'],
            #                                                                    "challengeId": event['args']['_id'],
            #                                                                    "date":
            #                                                                    })
            #               )
            commit_access_request = contract_instance.commitAccessRequest(event['args']['_id'], True,
                                                                          event['args']['_timeout'], 'discovery',
                                                                          'read', 'slaLink',
                                                                          'slaType',
                                                                          transact={'from': event['args']['_provider']})
            print('Provider has committed the order: %s' % commit_access_request)
            return commit_access_request
        except Exception as e:
            return e

    def publish_encrypted_token(self, event):
        contract_instance = self.contracts[OceanContracts.OACL][0]
        try:
            temp_public_key = contract_instance.getTempPubKey(event['args']['_paymentId'],
                                                              call={'from': event['args']['_receiver']})
            print("Public key: %s" % temp_public_key)
            jwt = encode({
                "iss": "resourceowner.com",
                "sub": "WorldCupDatasetForAnalysis",
                "iat": 1516239022,
                "exp": 1826790800,
                "consumer_pubkey": "Consumer Public Key",
                "temp_pubkey": temp_public_key,
                "request_id": "Request Identifier",
                "consent_hash": "Consent Hash",
                "resource_id": "Resource Identifier",
                "timeout": "Timeout comming from AUTH contract",
                "response_type": "Signed_URL",
                "resource_server_plugin": "Azure",
                "nonce": token_hex(32),
            }, self.encoding_key_pair.private_key)
            encJWT = enc(jwt, temp_public_key)
            # encJWT = enc(b'eyJhbGciOiJIUzI1', temp_public_key)
            # print("Delivering token jwt: %s" % jwt)
            print("Delivering token jwt: %s" % encJWT)
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       encJWT,
                                                                       transact={'from': event['args']['_receiver']})
            print('Provider has send the jwt: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            return e

    def release_payment(self, event):
        contract_instance = self.contracts[OceanContracts.OACL]

        if contract_instance.verifyAccessTokenDelivery(event['args']['_paymentId'],  # accessId
                                                       event['args'],  # consumerId
                                                       event,  # sig.v
                                                       event,  # sig.r
                                                       event,  # sig.s
                                                       transact={'from': event['args']['_receiver']}):
            return generate_sasurl(url)
