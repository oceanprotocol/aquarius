#!/usr/bin/env python
import json
import os
import time
from pathlib import Path

from ocean_lib.config import Config
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.data_token import DataToken
from ocean_lib.models.dtfactory import DTFactory
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.models.metadata import MetadataContract
from ocean_lib.ocean.util import get_web3_connection_provider, to_base_18
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.utils import privateKeyToAddress
from ocean_lib.web3_internal.wallet import Wallet
from ocean_lib.web3_internal.web3_provider import Web3Provider


def main():
    network = "ganache"
    private_key = os.getenv("EVENTS_TESTS_PRIVATE_KEY")
    network_rpc = os.getenv("EVENTS_RPC", "http://127.0.0.1:8545")

    config = Config(os.getenv("CONFIG_FILE"))
    ConfigProvider.set_config(config)
    # artifacts_path = os.getenv('ARTIFACTS_PATH', )
    artifacts_path = config.artifacts_path
    address_file = (
        Path(os.getenv("ADDRESS_FILE", os.path.join(artifacts_path, "address.json")))
        .expanduser()
        .resolve()
    )
    print(f"deploying contracts and saving addresses in {address_file}")

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

    print("****Deploy DataTokenTemplate: begin****")
    dt_address = DataToken.deploy(
        web3,
        deployer_wallet,
        artifacts_path,
        "Template Contract",
        "TEMPLATE",
        minter_addr,
        DataToken.DEFAULT_CAP_BASE,
        DTFactory.FIRST_BLOB,
        minter_addr,
    )
    addresses[DataToken.CONTRACT_NAME] = dt_address
    print("****Deploy DataTokenTemplate: done****\n")

    print("****Deploy DTFactory: begin****")
    dtfactory = DTFactory(
        DTFactory.deploy(web3, deployer_wallet, artifacts_path, dt_address, minter_addr)
    )
    addresses[DTFactory.CONTRACT_NAME] = dtfactory.address
    print("****Deploy DTFactory: done****\n")

    print("****Deploy BPool: begin****")
    bpool_address = BPool.deploy(web3, deployer_wallet, artifacts_path)
    bpool_template = BPool(bpool_address)
    addresses[BPool.CONTRACT_NAME] = bpool_address
    print("****Deploy BPool: done****\n")

    print("****Deploy 'BFactory': begin****")
    bfactory_address = BFactory.deploy(
        web3, deployer_wallet, artifacts_path, bpool_template.address
    )
    _ = BFactory(bfactory_address)
    addresses[BFactory.CONTRACT_NAME] = bfactory_address
    print("****Deploy 'BFactory': done****\n")

    print("****Deploy 'FixedRateExchange': begin****")
    addresses[FixedRateExchange.CONTRACT_NAME] = FixedRateExchange.deploy(
        web3, deployer_wallet, artifacts_path
    )
    print("****Deploy 'FixedRateExchange': done****\n")

    print("****Deploy 'Metadata': begin****")
    addresses[MetadataContract.CONTRACT_NAME] = MetadataContract.deploy(
        web3, deployer_wallet, artifacts_path
    )
    print("****Deploy 'Metadata': done****\n")

    if network == "ganache" and "Ocean" not in _addresses:
        print("****Deploy fake OCEAN: begin****")
        # For simplicity, hijack DataTokenTemplate.
        minter_addr = deployer_wallet.address
        OCEAN_cap = 1410 * 10 ** 6  # 1.41B
        OCEAN_cap_base = to_base_18(float(OCEAN_cap))
        OCEAN_token = DataToken(
            DataToken.deploy(
                web3,
                deployer_wallet,
                artifacts_path,
                "Ocean",
                "OCEAN",
                minter_addr,
                OCEAN_cap_base,
                "",
                minter_addr,
            )
        )
        addresses["Ocean"] = OCEAN_token.address
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
