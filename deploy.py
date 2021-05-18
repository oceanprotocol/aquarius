#!/usr/bin/env python
#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import os
import time

from ocean_lib.config import Config
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.data_token import DataToken
from ocean_lib.models.metadata import MetadataContract
from ocean_lib.ocean.util import get_web3_connection_provider, to_base_18
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.utils import privateKeyToAddress
from ocean_lib.web3_internal.wallet import Wallet
from ocean_lib.web3_internal.web3_provider import Web3Provider


def main():
    network = "development"
    private_key = os.getenv("EVENTS_TESTS_PRIVATE_KEY")
    network_rpc = os.getenv("EVENTS_RPC", "http://127.0.0.1:8545")

    config = Config(os.getenv("CONFIG_FILE"))
    ConfigProvider.set_config(config)
    # artifacts_path = os.getenv('ARTIFACTS_PATH', )
    artifacts_path = config.artifacts_path
    address_file = config.address_file

    Web3Provider.init_web3(provider=get_web3_connection_provider(network_rpc))
    ContractHandler.set_artifacts_path(artifacts_path)

    web3 = Web3Provider.get_web3()

    addresses = dict()

    if os.path.exists(address_file):
        with open(address_file) as f:
            network_addresses = json.load(f)
    else:
        network_addresses = {network: {}}

    _addresses = network_addresses[network]

    # ****SET ENVT****
    # grab vars
    factory_deployer_private_key = private_key

    # ****SEE FUNDS****
    print(
        "Keys:\n%s\n"
        % Wallet(web3=web3, private_key=factory_deployer_private_key).keysStr()
    )

    # ****DEPLOY****
    deployer_wallet = Wallet(web3, private_key=factory_deployer_private_key)
    minter_addr = deployer_wallet.address
    _ = 2 ** 255

    print("****Deploy 'Metadata': begin****")
    addresses[MetadataContract.CONTRACT_NAME] = MetadataContract.deploy(
        web3, deployer_wallet, artifacts_path
    )
    print("****Deploy 'Metadata': done****\n")

    if network == "development" and "Ocean" not in _addresses:
        print("****Deploy fake OCEAN: begin****")
        # For simplicity, hijack DataTokenTemplate.
        minter_addr = deployer_wallet.address
        OCEAN_cap = 1410 * 10 ** 6  # 1.41B
        OCEAN_cap_base = to_base_18(float(OCEAN_cap))
        OCEAN_token = DataToken(address=network_addresses["development"]["Ocean"])
        print("****Deploy fake OCEAN: done****\n")

        print("****Mint fake OCEAN: begin****")
        OCEAN_token.mint(minter_addr, OCEAN_cap_base, from_wallet=deployer_wallet)
        print("****Mint fake OCEAN: done****\n")

        print("****Distribute fake OCEAN: begin****")
        amt_distribute = 1000
        amt_distribute_base = to_base_18(float(amt_distribute))
        for key_label in ["EVENTS_TESTS_PRIVATE_KEY", "EVENTS_TESTS_PRIVATE_KEY2"]:
            key = os.environ.get(key_label)
            if not key:
                continue

            dst_address = privateKeyToAddress(key)
            try:
                OCEAN_token.transfer(
                    dst_address, amt_distribute_base, from_wallet=deployer_wallet
                )
            except ValueError:
                # handle nonce issue
                time.sleep(3)
                OCEAN_token.transfer(
                    dst_address, amt_distribute_base, from_wallet=deployer_wallet
                )

        print("****Distribute fake OCEAN: done****\n")

    network_addresses[network].update(addresses)

    with open(address_file, "w") as f:
        json.dump(network_addresses, f, indent=2)
    print(f"contracts deployed: {network_addresses}")
    return addresses


if __name__ == "__main__":
    main()
