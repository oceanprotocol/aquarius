#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from web3 import Web3


def sanitize_addresses(addresses):
    return [Web3.toChecksumAddress(a) for a in addresses if Web3.isAddress(a)]


def compare_eth_addresses(address, checker, logger):
    """
    Compare two addresses and return TRUE if there is a match
    :param str address: Address
    :param str checker: Address to compare with
    :param logger: instance of logging
    :return: boolean
    """
    logger.debug("compare_eth_addresses address: %s" % address)
    logger.debug("compare_eth_addresses checker: %s" % checker)
    if not Web3.isAddress(address):
        logger.debug("Address is not web3 valid")
        return False
    if not Web3.isAddress(checker):
        logger.debug("Checker is not web3 valid")
        return False
    return Web3.toChecksumAddress(address) == Web3.toChecksumAddress(checker)
