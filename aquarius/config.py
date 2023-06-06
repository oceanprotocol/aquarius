#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import configparser
import os

from aquarius.events.http_provider import get_web3_connection_provider
from web3 import Web3


def get_version():
    conf = configparser.ConfigParser()
    conf.read(".bumpversion.cfg")
    return conf["bumpversion"]["current_version"]


def get_config_chain_id():
    config_rpc = os.getenv("CONFIG_NETWORK_URL")
    provider = get_web3_connection_provider(config_rpc)
    web3 = Web3(provider)

    return web3.eth.chain_id
