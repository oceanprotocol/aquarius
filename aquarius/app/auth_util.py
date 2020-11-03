import json
import os

from ocean_lib.web3_internal.web3helper import Web3Helper
from web3 import Web3


def get_signer_address(message, signature, logger):
    """
    Get signer address of a previous signed message
    :param str message: Message
    :param str signature: Signature obtain with web3.eth.personal.sign
    :param logger: logging object
    :return: Address or None in case of error
    """
    try:
        logger.debug(f'got "{message}" as a message')
        address_recovered = Web3Helper.personal_ec_recover(message, signature)
        logger.debug(f'got "{address_recovered}" as address_recovered')
        return address_recovered
    except Exception as e:
        logger.error(f'get_signer_address: {e}')
        return None


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
    logger.debug('compare_eth_addresses address: %s' % address)
    logger.debug('compare_eth_addresses checker: %s' % checker)
    if not Web3.isAddress(address):
        logger.debug("Address is not web3 valid")
        return False
    if not Web3.isAddress(checker):
        logger.debug("Checker is not web3 valid")
        return False
    return Web3.toChecksumAddress(address) == Web3.toChecksumAddress(checker)


def has_update_request_permission(address):
    vip_list = os.getenv('AQUA_VIP_ACCOUNTS', '[]')
    try:
        vip_list = json.loads(vip_list)
        return isinstance(vip_list, list) and bool(address in vip_list)
    except Exception:
        return False
