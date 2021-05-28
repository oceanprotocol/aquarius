#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
import time
from pathlib import Path
import pkg_resources

from jsonsempai import magic  # noqa: F401
from artifacts import address as contract_addresses, Metadata
from aquarius.events.http_provider import CustomHTTPProvider
from web3 import Web3

from aquarius.app.util import get_bool_env_value


ENV_ADDRESS_FILE = "ADDRESS_FILE"
ENV_ARTIFACTS_PATH = "ARTIFACTS_PATH"

ADDRESS_FILE_NAME = "address.json"
METADATA_ABI_FILE_NAME = "Metadata.json"


def get_network_name():
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
    account = w3.eth.account.privateKeyToAccount(private_key)
    _contract = w3.eth.contract(abi=_json["abi"], bytecode=_json["bytecode"])
    built_tx = _contract.constructor(*args).buildTransaction({"from": account.address})
    if "gas" not in built_tx:
        built_tx["gas"] = w3.eth.estimateGas(built_tx)
    raw_tx = sign_tx(w3, built_tx, private_key)
    tx_hash = w3.eth.sendRawTransaction(raw_tx)
    time.sleep(3)
    try:
        address = w3.eth.getTransactionReceipt(tx_hash)["contractAddress"]
        return address
    except Exception:
        print(f"tx not found: {tx_hash.hex()}")
        raise


def sign_tx(web3, tx, private_key):
    account = web3.eth.account.privateKeyToAccount(private_key)
    nonce = web3.eth.getTransactionCount(account.address)
    gas_price = int(web3.eth.gasPrice / 100)
    tx["gasPrice"] = gas_price
    tx["nonce"] = nonce
    signed_tx = web3.eth.account.signTransaction(tx, private_key)
    return signed_tx.rawTransaction


def deploy_datatoken(web3, private_key, name, symbol, minter_address):
    dt_file_path = os.path.join(get_artifacts_path(), "DataTokenTemplate.json")
    return deploy_contract(
        web3,
        json.load(open(dt_file_path)),
        private_key,
        name,
        symbol,
        minter_address,
        1000,
        "no blob",
        minter_address,
    )


def get_artifacts_path():
    """Returns Path to the artifacts directory where ocean ABIs are stored.
    Checks envvar first, fallback to artifacts included with ocean-contracts.
    """
    env_path = os.getenv(ENV_ARTIFACTS_PATH)
    return (
        Path(env_path).expanduser().resolve()
        if env_path
        else Path(contract_addresses.__file__).parent.expanduser().resolve()
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
    """Returns a Contract built from the Metadata contract address and ABI"""
    address_file = get_address_file()

    with open(address_file) as f:
        address_json = json.load(f)

    network = get_network_name()
    address = address_json[network]["Metadata"]

    env_path = os.getenv(ENV_ARTIFACTS_PATH)

    if env_path:
        abi_file = (
            Path(env_path).joinpath(METADATA_ABI_FILE_NAME).expanduser().resolve()
        )

        with open(abi_file) as f:
            abi_json = json.load(f)

        abi = abi_json["abi"]
    else:
        abi = Metadata.abi

    return web3.eth.contract(address=address, abi=abi)


def get_datatoken_info(web3, token_address):
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
    network_rpc = os.environ.get("EVENTS_RPC", "http:127.0.0.1:8545")
    if _logger:
        _logger.info(
            f"EventsMonitor: starting with the following values: rpc={network_rpc}"
        )

    provider = CustomHTTPProvider(network_rpc)
    web3 = Web3(provider)

    if (
        get_bool_env_value("USE_POA_MIDDLEWARE", 0)
        or get_network_name().lower() == "rinkeby"
    ):
        from web3.middleware import geth_poa_middleware

        web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    return web3
