import json
import os
import time
from pathlib import Path

from web3.exceptions import TransactionNotFound


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
    except TransactionNotFound:
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
    return os.environ.get('ARTIFACTS_PATH', './aquarius/artifacts')


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
