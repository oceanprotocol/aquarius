#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from eth_account.messages import defunct_hash_message

def get_signer_address(message, signature,web3,logger):
    '''
    Get signer address of a previous signed message
    :param str message: Message
    :param str signature: Signature obtain with web3.eth.personal.sign
    :return: Address or None in case of error
    '''
    try:
        logger.debug('got %s as a message' % message)
        message_hash = defunct_hash_message(text=message)
        logger.debug('got %s as a message_hash' % message_hash)    
        address_recovered = web3.eth.account.recoverHash(message_hash, signature=signature)
        logger.debug('got %s as address_recovered' % address_recovered)    
        return address_recovered
    except Exception as e:
        logger.error(e)
        return None  

def compare_eth_addresses(address, checker, web3):
    '''
    Compare two addresses and return TRUE if there is a match
    :param str address: Address
    :param str checker: Address to compare with
    :return: boolean
    '''
    return web3.toChecksumAddress(address) == web3.toChecksumAddress(checker)
    

def _can_update_did(ddo, updated, signature,web3,logger):
    '''
    Check if the signer is allowed to update the DDO
    :param record ddo: DDO that has to be updated
    :param str updated: Updated field passed by user
    :param str signature: Signature of the updated field, using web3.eth.personal.sign
    :return: boolean TRUE if the signer is allowed to update the DDO
    '''
    if ddo['updated'] is None or updated is None or ddo['updated']!=updated:
        return False
    address=get_signer_address(updated, signature,web3,logger)
    if address is None:
        return False
    if compare_eth_addresses(address, ddo['publicKey'][0]['owner'],web3) is True:
        return True
    return False

def _can_update_did_from_allowed_updaters(ddo, updated, signature,web3,logger):
    '''
    Check if the signer is allowed to update the DDO. List of signers is taken from ENV variabile RATING_ALLOWED_UPDATER
    :param record ddo: DDO that has to be updated
    :param str updated: Updated field passed by user
    :param str signature: Signature of the updated field, using web3.eth.personal.sign
    :return: boolean TRUE if the signer is allowed to update the DDO
    '''
    allowedUpdater=os.environ.get("RATING_ALLOWED_UPDATER")
    if ddo['updated'] is None or updated is None or ddo['updated']!=updated:
        logger.debug("missmatch updated")
        return False
    address=get_signer_address(updated, signature,web3,logger)
    if address is None:
        logger.debug("signer_address is none")
        return False
    if allowedUpdater is None:
        logger.debug("allowedUpdater is None")
        return False
    if compare_eth_addresses(address, allowedUpdater,web3) is True:
        return True
    return False
