import os
import json
from web3 import Web3, HTTPProvider, TestRPCProvider
from web3.contract import ConciseContract

# pwd = os.path.dirname(os.path.abspath(__file__))
# contracts_folder = '%s/../../../plankton-keeper/build/contracts' % pwd


def convert_to_bytes(data):
    return Web3.toBytes(text=data)


def convert_to_string(data):
    return Web3.toHex(data)


class OceanContracts(object):
    def __init__(self, host, port, account=None):
        self.host = host
        self.port = port

        self.web3 = OceanContracts.connect_web3(self.host, self.port)
        self.account = self.web3.eth.accounts[0] if account is None else account

        self.contracts_abis_path = ''
        self.contracts = {}

    def init_contracts(self, contracts_folder, contracts_addresses):
        self.contracts_abis_path = contracts_folder
        for contract_name, address in contracts_addresses.iteritems():
            contract_abi_file = os.path.join(self.contracts_abis_path, contract_name, 'json')
            self.contracts[contract_name] = self.get_contract_instance(contract_abi_file, address)

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

    def authorizeAccess(self, asset_id, url, signed_url, contract_address):
        contract_instance = self.contracts['Market']
        tx_hash = contract_instance.publish(asset_id, url, signed_url, transact={'from': self.account})
        receipt = self.get_tx_receipt(tx_hash)
        return contract_instance.events.AssetPublished().processReceipt(receipt)

    def list_published_asset(self):
        contract_instance = self.contracts['Market']
        tx_hash = contract_instance.getListAssets(transact={'from': self.account})
        return self.get_tx_receipt(tx_hash)

    def list_assets(self):
        contract_instance = self.contracts['Market']
        return contract_instance.getListAssets()
