#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
import time
import logging
from pathlib import Path
import pkg_resources

from jsonsempai import magic  # noqa: F401
from artifacts import address as contract_addresses, Metadata, DataTokenTemplate
from aquarius.events.http_provider import get_web3_connection_provider
from web3 import Web3

from aquarius.app.util import get_bool_env_value

logger = logging.getLogger(__name__)
ENV_ADDRESS_FILE = "ADDRESS_FILE"


def get_network_name():
    """
    :return str: network name
    """
    network_name = os.getenv("NETWORK_NAME", None)

    if not network_name:
        network = os.getenv("EVENTS_RPC")
        if network.startswith("wss://"):
            network_name = network[len("wss://") :].split(".")[0]
        elif not network.startswith("http"):
            network_name = network
        else:
            network_name = os.getenv("NETWORK_NAME")

        if not network_name:
            raise AssertionError("Cannot figure out the network name.")

    return network_name


def deploy_contract(w3, _json, private_key, *args):
    """
    :param w3: Web3 object instance
    :param private_key: Private key of the account
    :param _json: Json content of artifact file
    :param *args: arguments to be passed to be constructor of the contract
    :return: address of deployed contract
    """
    account = w3.eth.account.from_key(private_key)
    _contract = w3.eth.contract(abi=_json["abi"], bytecode=_json["bytecode"])
    built_tx = _contract.constructor(*args).buildTransaction({"from": account.address})
    if "gas" not in built_tx:
        built_tx["gas"] = w3.eth.estimate_gas(built_tx)
    raw_tx = sign_tx(w3, built_tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    time.sleep(3)
    try:
        address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]
        return address
    except Exception:
        print(f"tx not found: {tx_hash.hex()}")
        raise


def sign_tx(web3, tx, private_key):
    """
    :param web3: Web3 object instance
    :param tx: transaction
    :param private_key: Private key of the account
    :return: rawTransaction (str)
    """
    account = web3.eth.account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)
    gas_price = int(web3.eth.gas_price / 100)
    tx["gasPrice"] = gas_price
    tx["nonce"] = nonce
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    return signed_tx.rawTransaction


def deploy_datatoken(web3, private_key, name, symbol, minter_address):
    """
    :param web3: Web3 object instance
    :param private_key: Private key of the account
    :param name: Name of the datatoken to be deployed
    :param symbol: Symbol of the datatoken to be deployed
    :param minter_address: Account address
    :return: Address of the deployed contract
    """
    return deploy_contract(
        web3,
        {"abi": DataTokenTemplate.abi, "bytecode": DataTokenTemplate.bytecode},
        private_key,
        name,
        symbol,
        minter_address,
        1000,
        "no blob",
        minter_address,
    )


def get_address_file():
    """Returns Path to the address.json file
    Checks envvar first, fallback to address.json included with ocean-contracts.
    """
    env_file = os.getenv(ENV_ADDRESS_FILE)
    return (
        Path(env_file).expanduser().resolve()
        if env_file
        else Path(contract_addresses.__file__).expanduser().resolve()
    )


def get_metadata_contract(web3):
    """Returns a Contract built from the Metadata contract address (or ENV) and ABI"""
    address = os.getenv("METADATA_CONTRACT_ADDRESS", None)
    if not address:
        address_file = get_address_file()
        with open(address_file) as f:
            address_json = json.load(f)
        network = get_network_name()
        address = address_json[network]["Metadata"]
    abi = Metadata.abi

    return web3.eth.contract(address=address, abi=abi)


def get_metadata_start_block():
    """Returns the block number to use as start"""
    block_number = int(os.getenv("METADATA_CONTRACT_BLOCK", 0))
    if not block_number:
        address_file = get_address_file()
        with open(address_file) as f:
            address_json = json.load(f)
        network = get_network_name()
        if "startBlock" in address_json[network]:
            block_number = address_json[network]["startBlock"]

    return block_number


def get_datatoken_info(web3, token_address):
    """
    :param token_address: Datatoken address
    :return: Json object as below
        ```
        {
        "address": <token_address>,
        "name": <contract_name>,
        "symbol": <symbol>,
        "decimals":  <decimals>,
        "totalSupply": <totalSupply>,
        "cap": <cap>,
        "minter": <minter>,
        "minterBalance": <balance of minter>,
        }
        ```
    """
    token_address = Web3.toChecksumAddress(token_address)
    dt_abi_path = Path(
        pkg_resources.resource_filename("aquarius", "events/datatoken_abi.json")
    ).resolve()
    with open(dt_abi_path) as f:
        datatoken_abi = json.load(f)

    dt = web3.eth.contract(address=token_address, abi=datatoken_abi)
    decimals = dt.functions.decimals().call()
    cap_orig = dt.functions.cap().call()

    return {
        "address": token_address,
        "name": dt.functions.name().call(),
        "symbol": dt.functions.symbol().call(),
        "decimals": decimals,
        "cap": float(cap_orig / (10 ** decimals)),
    }


def setup_web3(config_file, _logger=None):
    """
    :param config_file: Web3 object instance
    :param _logger: Logger instance
    :return: web3 instance
    """
    network_rpc = os.environ.get("EVENTS_RPC", "http:127.0.0.1:8545")
    if _logger:
        _logger.info(
            f"EventsMonitor: starting with the following values: rpc={network_rpc}"
        )

    provider = get_web3_connection_provider(network_rpc)
    web3 = Web3(provider)

    if (
        get_bool_env_value("USE_POA_MIDDLEWARE", 0)
        or get_network_name().lower() == "rinkeby"
    ):
        from web3.middleware import geth_poa_middleware

        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    return web3
