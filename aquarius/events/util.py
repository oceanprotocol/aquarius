import json
import os
import time
from pathlib import Path

from ocean_lib.ocean.util import get_contracts_addresses
from ocean_lib.web3_internal.web3helper import Web3Helper
from web3 import Web3

from aquarius.events.http_provider import CustomHTTPProvider


def get_web3_connection_provider(network_url):
    if network_url.startswith('http'):
        provider = CustomHTTPProvider(network_url)
    else:
        assert network_url.startswith('ws'), f'network url must start with either https or wss'
        provider = Web3.WebsocketProvider(network_url)

    return provider


def get_network_name():
    try:
        network_name = Web3Helper.get_network_name().lower()
    except ValueError:
        network = os.getenv('EVENTS_RPC')
        if network.startswith('wss://'):
            network_name = network[len('wss://'):].split('.')[0]
        elif not network.startswith('http'):
            network_name = network
        else:
            network_name = os.getenv('NETWORK_NAME')

        if not network_name:
            raise AssertionError(f'Cannot figure out the network name.')

    return network_name


def prepare_contracts(web3, config):
    addresses = get_contracts_addresses(get_network_name(), config)
    if not addresses:
        raise AssertionError(f'Cannot find contracts addresses for network {get_network_name()}')

    addresses = {name: web3.toChecksumAddress(a) for name, a in addresses.items()}
    return addresses

def deploy_contract(w3, _json, private_key, *args):
    account = w3.eth.account.privateKeyToAccount(private_key)
    _contract = w3.eth.contract(abi=_json['abi'], bytecode=_json['bytecode'])
    built_tx = _contract.constructor(*args).buildTransaction({'from': account.address})
    if 'gas' not in built_tx:
        built_tx['gas'] = w3.eth.estimateGas(built_tx)
    raw_tx = sign_tx(w3, built_tx, private_key)
    tx_hash = w3.eth.sendRawTransaction(raw_tx)
    time.sleep(3)
    try:
        address = w3.eth.getTransactionReceipt(tx_hash)['contractAddress']
        return address
    except Exception:
        print(f'tx not found: {tx_hash.hex()}')
        raise


def sign_tx(web3, tx, private_key):
    account = web3.eth.account.privateKeyToAccount(private_key)
    nonce = web3.eth.getTransactionCount(account.address)
    gas_price = int(web3.eth.gasPrice / 100)
    tx['gasPrice'] = gas_price
    tx['nonce'] = nonce
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    return signed_tx.rawTransaction


def deploy_datatoken(web3, private_key, name, symbol, minter_address):
    dt_file_path = os.path.join(get_artifacts_path(), 'DataTokenTemplate.json')
    return deploy_contract(
        web3, json.load(open(dt_file_path)), private_key,
        name, symbol, minter_address, 1000, 'no blob', minter_address
    )


def get_artifacts_path():
    path = os.environ.get('ARTIFACTS_PATH', './aquarius/artifacts')
    return Path(path).expanduser().resolve()


def get_contract_address_and_abi_file():
    artifacts_path = get_artifacts_path()
    contract_abi_file = Path(os.path.join(artifacts_path, 'Metadata.json')).expanduser().resolve()
    address_file = os.environ.get('ADDRESS_FILE', os.path.join(artifacts_path, 'address.json'))
    address_file = Path(address_file).expanduser().resolve()
    contract_address = read_ddo_contract_address(address_file, network=os.environ.get('NETWORK_NAME', 'ganache'))
    return contract_address, contract_abi_file


def read_ddo_contract_address(file_path, name='Metadata', network='ganache'):
    with open(file_path) as f:
        network_to_address = json.load(f)
        return network_to_address[network][name]


def get_metadata_contract(web3):
    contract_address, abi_file = get_contract_address_and_abi_file()
    abi_json = json.load(open(abi_file))
    return web3.eth.contract(address=contract_address, abi=abi_json['abi'])