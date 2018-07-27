import os
import json
import time, site
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract
from provider_backend.config_parser import load_config_section
from provider_backend.myapp import app
from provider_backend.constants import ConfigSections
from provider_backend.acl.acl import enc, encode
from threading import Thread


config_file = app.config['CONFIG_FILE']
conf = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)


def convert_to_bytes(data):
    return Web3.toBytes(text=data)


def convert_to_string(data):
    return Web3.toHex(data)


def get_contracts_path():
    try:
        if 'contracts.folder' in conf:
            return conf['contracts.folder']
        elif os.getenv('VIRTUAL_ENV') is not None:
            return "%s/contracts" % (os.getenv('VIRTUAL_ENV'))
        else:
            return "%s/contracts" % site.getsitepackages()[0]
    except Exception as e:
        return e



class OceanContracts(object):

    def __init__(self, host=conf['keeper.host'], port=conf['keeper.port'], account=None):
        self.host = host
        self.port = port
        self.web3 = OceanContracts.connect_web3(self.host, self.port)
        self.account = self.web3.eth.accounts[0] if account is None else account
        self.contracts_abis_path = get_contracts_path()
        self.concise_contracts = {}
        self.contracts = {}

    def init_contracts(self, market_address=conf['market.address'], auth_address=conf['auth.address'], token_address=conf['token.address']):
        # TODO Improve load of contracts
        for contract_name in os.listdir(self.contracts_abis_path):
            if contract_name == 'Market.json':
                self.concise_contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), market_address, True)
                self.contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), market_address, False)
            elif contract_name == 'OceanToken.json':
                self.concise_contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), token_address, True)
                self.contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), token_address, False)
            else:
                self.concise_contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), auth_address, True)
                self.contracts[contract_name] = self.get_contract_instance(
                    os.path.join(self.contracts_abis_path, contract_name), auth_address, False)

    @staticmethod
    def connect_web3(host, port='8545'):
        return Web3(HTTPProvider("http://%s:%s" % (host, port)))

    def get_contract_instance(self, contract_file, contract_address, concise=False):
        with open(contract_file, 'r') as abi_definition:
            abi = json.load(abi_definition)
            if concise:
                return self.web3.eth.contract(
                    address=self.web3.toChecksumAddress(contract_address),
                    abi=abi['abi'],
                    ContractFactoryClass=ConciseContract)
            else:
                return self.web3.eth.contract(
                    address=self.web3.toChecksumAddress(contract_address),
                    abi=abi['abi'])

    def get_tx_receipt(self, tx_hash):
        self.web3.eth.waitForTransactionReceipt(tx_hash)
        return self.web3.eth.getTransactionReceipt(tx_hash)

    def watch_event(self, contract_name, event_name, callback, interval, fromBlock=0, toBlock='latest',filters=None,):
        event_filter = self.install_filter(
            contract_name, event_name, fromBlock, toBlock, filters
        )
        event_filter.poll_interval= 500
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
        contract_instance = self.contracts[contract_name + ".json"]
        event = getattr(contract_instance.events, event_name)
        eventFilter = event.createFilter(
            fromBlock=fromBlock, toBlock=toBlock, argument_filters=filters
        )
        return eventFilter

    def commit_access_request(self, event):
        contract_instance = self.concise_contracts['Auth.json']
        try:
            # TODO register metadata of the request.
            # url_for("/register")
            # assets.register()
            commit_access_request = contract_instance.commitAccessRequest(event['args']['_id'], True, event['args']['_timeout'], 'discovery',
                                              'read', 'slaLink',
                                              'slaType',transact={'from': event['args']['_provider']})
            print('Provider has committed the order: %s' % commit_access_request)
            return commit_access_request
        except Exception as e:
            return e

    def publish_encrypted_token(self, event):
        contract_instance = self.concise_contracts['Auth.json']
        try:
            public_key = contract_instance.getTempPubKey(event['args']['_paymentId'],
                                                         call={'from': event['args']['_receiver']})
            print("Public key: %s" % public_key)
            jwt=encode(
            {
                "iss": "resourceowner.com",
                "sub": "WorldCupDatasetForAnalysis",
                "iat": 1516239022,
                "exp": 1526790800,
                "consumer_pubkey": public_key,
                "temp_pubkey": "Temp. Public Key for Encryption",
                "request_id": "Request Identifier",
                "consent_hash": "Consent Hash",
                "resource_id": "Resource Identifier",
                "timeout": "Timeout comming from AUTH contract",
                "response_type": "Signed_URL",
                "resource_server_plugin": "Azure",
            }, public_key)
            # encJWT = enc(public_key, jwt)
            print("Delivering token jwt: %s" % jwt)
            deliver_acces_token = contract_instance.deliverAccessToken(event['args']['_paymentId'],
                                                                       jwt,
                                                                       transact={'from': event['args']['_receiver']})
            print('Provider has send the jwt: %s' % deliver_acces_token)
            return deliver_acces_token
        except Exception as e:
            return e

    #
    # def release_payment(self, event):
    #     contract_instance = self.concise_contracts['Auth.json']
    #
    #     if contract_instance.verifyAccessTokenDelivery(event['args']['_paymentId'], #accessId
    #                                                        event['args'],               #consumerId
    #                                                        event,                       #sig.v
    #                                                        event,                       #sig.r
    #                                                        event,                       #sig.s
    #                                                        transact={'from': event['args']['_receiver']}):
    #         return generate_sasurl(url)
