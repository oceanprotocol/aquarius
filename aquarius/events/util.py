import json
import os
import time
from pathlib import Path

from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.data_token import DataToken
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.models.metadata import MetadataContract
from ocean_lib.ocean.util import get_contracts_addresses, from_base_18
from ocean_lib.web3_internal.web3helper import Web3Helper
from web3 import Web3


def get_network_name():
    try:
        network_name = os.getenv('NETWORK_NAME')
        if not network_name:
            network_name = Web3Helper.get_network_name().lower()
    except Exception:
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
    path = ConfigProvider.get_config().artifacts_path
    return Path(path).expanduser().resolve()


def get_address_file(artifacts_path):
    address_file = os.environ.get('ADDRESS_FILE', os.path.join(artifacts_path, 'address.json'))
    return Path(address_file).expanduser().resolve()


def get_contract_address_and_abi_file(name):
    file_name = name + '.json'
    artifacts_path = get_artifacts_path()
    contract_abi_file = Path(os.path.join(artifacts_path, file_name)).expanduser().resolve()
    address_file = get_address_file(artifacts_path)
    contract_address = read_ddo_contract_address(address_file, name, network=os.environ.get('NETWORK_NAME', 'ganache'))
    return contract_address, contract_abi_file


def read_ddo_contract_address(file_path, name, network='ganache'):
    with open(file_path) as f:
        network_to_address = json.load(f)
        return network_to_address[network][name]


def get_metadata_contract(web3):
    contract_address, abi_file = get_contract_address_and_abi_file(MetadataContract.CONTRACT_NAME)
    abi_json = json.load(open(abi_file))
    return web3.eth.contract(address=contract_address, abi=abi_json['abi'])


def get_exchange_contract(web3):
    contract_address, abi_file = get_contract_address_and_abi_file(FixedRateExchange.CONTRACT_NAME)
    abi_json = json.load(open(abi_file))
    return web3.eth.contract(address=contract_address, abi=abi_json['abi'])


def get_datatoken_info(token_address):
    token_address = Web3.toChecksumAddress(token_address)
    dt = DataToken(token_address)
    contract = dt.contract_concise
    minter = contract.minter()
    return {
        'address': token_address,
        'name': contract.name(),
        'symbol': contract.symbol(),
        'decimals': contract.decimals(),
        'totalSupply': from_base_18(contract.totalSupply()),
        'cap': from_base_18(contract.cap()),
        'minter': minter,
        'minterBalance': dt.token_balance(minter)
    }
