import os

from eth_account import Account
from eth_account.messages import encode_defunct
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
        logger.debug('got %s as a message' % message)
        signable_message = encode_defunct(text=message)
        logger.debug(f'got {signable_message} as a message_hash')
        address_recovered = Account.recover_message(
            signable_message=signable_message,
            signature=signature
        )
        logger.debug('got %s as address_recovered' % address_recovered)
        return address_recovered
    except Exception as e:
        logger.error(f'get_signer_address: {e}')
        return None


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


def can_update_did(ddo, updated, signature, logger):
    """
    Check if the signer is allowed to update the DDO
    :param record ddo: DDO that has to be updated
    :param str updated: Updated field passed by user
    :param str signature: Signature of the updated field, using web3.eth.personal.sign
    :param logger: instance of logging
    :return: boolean TRUE if the signer is allowed to update the DDO
    """
    if ddo['updated'] is None or updated is None or ddo['updated'] != updated:
        return False
    address = get_signer_address(updated, signature, logger)
    if address is None:
        return False
    if compare_eth_addresses(address, ddo['publicKey'][0]['owner'], logger) is True:
        return True
    return False


def can_update_did_from_allowed_updaters(ddo, updated, signature, logger):
    """
    Check if the signer is allowed to update the DDO. List of signers is taken from ENV variabile RATING_ALLOWED_UPDATER
    :param record ddo: DDO that has to be updated
    :param str updated: Updated field passed by user
    :param str signature: Signature of the updated field, using web3.eth.personal.sign
    :param logger: instance of logging
    :return: boolean TRUE if the signer is allowed to update the DDO
    """
    allowed_updater = os.environ.get("RATING_ALLOWED_UPDATER")
    logger.debug('got RATING_ALLOWED_UPDATER: %s' % allowed_updater)
    if ddo['updated'] is None or updated is None or ddo['updated'] != updated:
        logger.debug("mismatch updated")
        return False
    address = get_signer_address(updated, signature, logger)
    if address is None:
        logger.debug("signer_address is none")
        return False
    if allowed_updater is None:
        logger.debug("allowedUpdater is None")
        return False
    if compare_eth_addresses(address, allowed_updater, logger) is True:
        return True
    return False
