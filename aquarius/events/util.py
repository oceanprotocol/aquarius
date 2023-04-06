#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from eth_utils import remove_0x_prefix
from eth_utils.address import to_checksum_address, is_address
import artifacts
import hashlib
import json
import logging
import os
import time
from pathlib import Path

from web3 import Web3
from web3.exceptions import ExtraDataLengthError

import addresses
from aquarius.events.http_provider import get_web3_connection_provider
from web3.logs import DISCARD


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
        elif network.startswith("https"):
            network_name = network[len("https://") :].split(".")[0]
        elif network.startswith("http"):
            network_name = network[len("http://") :].split(".")[0]
        else:
            network_name = network

        if not network_name:
            raise AssertionError("Cannot figure out the network name.")

    return network_name


def get_start_block_by_chain_id(chain_id: int) -> str:
    """Return the contract address with the given name and chain id"""
    with open(get_address_file(), "r") as address_json:
        addresses = json.load(address_json)

    return next(
        network_values["startBlock"]
        for network_values in addresses.values()
        if network_values["chainId"] == chain_id
    )


def get_defined_block(chain_id: int):
    """Retrieves the block either from envvar, either from address.json file."""
    if "BFACTORY_BLOCK" in os.environ:
        return int(os.getenv("BFACTORY_BLOCK"))

    return get_start_block_by_chain_id(chain_id)


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


def deploy_datatoken(w3, account, name, symbol):
    """
    :param web3: Web3 object instance
    :param private_key: Private key of the account
    :param name: Name of the datatoken to be deployed
    :param symbol: Symbol of the datatoken to be deployed
    :param minter_address: Account address
    :return: Address of the deployed contract
    """
    dt_factory = get_dt_factory(w3)

    built_tx = dt_factory.functions.deployERC721Contract(
        name,
        symbol,
        1,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        "http://oceanprotocol.com/nft",
        True,
        to_checksum_address(account.address),
    ).build_transaction({"from": account.address, "gasPrice": w3.eth.gas_price})

    raw_tx = sign_tx(w3, built_tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(raw_tx)

    time.sleep(3)
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)

        return (
            dt_factory.events.NFTCreated()
            .process_receipt(receipt, errors=DISCARD)[0]
            .args.newTokenAddress
        )
    except Exception:
        print(f"tx not found: {tx_hash.hex()}")
        raise Exception(f"tx not found: {tx_hash.hex()}")


def get_address_of_type(web3, chain_id=None, address_type=None):
    chain_id = chain_id if chain_id else web3.eth.chain_id
    address_file = get_address_file()

    with open(address_file) as f:
        address_json = json.load(f)

    correspondence = {
        elem["chainId"]: elem[address_type]
        for elem in address_json.values()
        if "chainId" in elem and address_type in elem
    }

    if chain_id not in correspondence:
        raise Exception(b"No {address_type} factory configured for chain id")

    return correspondence[chain_id]


def get_contract(web3, contract_name, address):
    abi = get_contract_definition(contract_name)["abi"]

    return web3.eth.contract(address=to_checksum_address(address), abi=abi)


def get_contract_definition(contract_name: str):
    """Returns the abi JSON for a contract name."""
    path = os.path.join(artifacts.__file__, "..", f"{contract_name}.json")
    path = Path(path).expanduser().resolve()

    if not path.exists():
        raise TypeError("Contract name does not exist in artifacts.")

    with open(path) as f:
        return json.load(f)


def get_dt_factory(web3, chain_id=None):
    chain_id = chain_id if chain_id else web3.eth.chain_id
    address = get_address_of_type(web3, chain_id, "ERC721Factory")

    return get_contract(web3, "ERC721Factory", address)


def get_fre(web3, chain_id=None, address=None):
    chain_id = chain_id if chain_id else web3.eth.chain_id
    if not address:
        address = get_address_of_type(web3, chain_id, "FixedPrice")

    return get_contract(web3, "FixedRateExchange", address)


def get_dispenser(web3, chain_id=None, address=None):
    chain_id = chain_id if chain_id else web3.eth.chain_id
    if not address:
        address = get_address_of_type(web3, chain_id, "Dispenser")

    return get_contract(web3, "Dispenser", address)


def get_factory_contract(web3, chain_id=None):
    chain_id = chain_id if chain_id else web3.eth.chain_id
    address = get_address_of_type(web3, chain_id, "Router")

    return get_contract(web3, "FactoryRouter", address)


def get_nft_contract(web3, address):
    address = to_checksum_address(address)
    return get_contract(web3, "ERC721Template", address)


def get_erc20_contract(web3, address):
    address = to_checksum_address(address)
    return get_contract(web3, "ERC20Template", address)


def is_approved_fre(web3, address, chain_id=None):
    """Returns True if a fre is approved by Factory"""
    valid = False
    try:
        router = get_factory_contract(web3, chain_id)
        valid = router.caller.isFixedRateContract(address)
    except Exception as e:
        logger.warning(f"Failed to check is {address} is an approved fre:  {e}")
    return valid


def is_approved_dispenser(web3, address, chain_id=None):
    """Returns True if a dispenser is approved by Factory"""
    valid = False
    try:
        router = get_factory_contract(web3, chain_id)
        valid = router.caller.isDispenserContract(address)
    except Exception as e:
        logger.warning(f"Failed to check is {address} is an approved dispenser:  {e}")
    return valid


def get_address_file():
    """Returns Path to the address.json file
    Checks envvar first, fallback to address.json included with ocean-contracts.
    """
    env_file = os.getenv(ENV_ADDRESS_FILE)
    return (
        Path(env_file).expanduser().resolve()
        if env_file
        else Path(os.path.join(addresses.__file__, "..", "address.json"))
        .expanduser()
        .resolve()
    )


def get_metadata_start_block():
    """Returns the block number to use as start"""
    block_number = int(os.getenv("METADATA_CONTRACT_BLOCK", 0))
    if not block_number:
        address_file = get_address_file()
        with open(address_file) as f:
            address_json = json.load(f)
        network = get_network_name()
        block_number = (
            address_json[network]["startBlock"]
            if "startBlock" in address_json[network]
            else 0
        )

    return block_number


def setup_web3(_logger=None):
    """
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

    try:
        web3.eth.get_block("latest")
    except ExtraDataLengthError:
        from web3.middleware import geth_poa_middleware

        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    return web3


def make_did(data_nft_address, chain_id):
    if not is_address(data_nft_address.lower()):
        return None
    return "did:op:" + remove_0x_prefix(
        Web3.to_hex(
            hashlib.sha256(
                (to_checksum_address(data_nft_address) + str(chain_id)).encode("utf-8")
            ).digest()
        )
    )


def update_did_state(es_instance, nft_address, chain_id, txid, valid, error):
    if not es_instance:
        return
    es_instance.update_did_state(nft_address, chain_id, txid, valid, error)
