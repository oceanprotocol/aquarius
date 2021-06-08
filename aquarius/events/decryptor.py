#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import ecies
import eth_keys
import json
import logging
import lzma as Lzma

from aquarius.app.util import get_bool_env_value

logger = logging.getLogger(__name__)


class Decryptor:
    def __init__(self, ecies_account):
        """Initialises Decryptor object based on ecies account."""
        self._ecies_account = ecies_account

    def ecies_decrypt(self, rawddo):
        if self._ecies_account is not None:
            key = eth_keys.KeyAPI.PrivateKey(self._ecies_account.key)
            rawddo = ecies.decrypt(key.to_hex(), rawddo)
        return rawddo

    def decode_ddo(self, rawddo, flags):
        logger.debug(f"flags: {flags}")
        logger.debug(f"Before unpack rawddo: {rawddo}")

        if len(flags) < 1:
            logger.debug("Set check_flags to 0!")
            check_flags = 0
        else:
            check_flags = flags[0]

        _only_encrypted_ddo = get_bool_env_value("ONLY_ENCRYPTED_DDO", 0)
        if _only_encrypted_ddo and (not check_flags & 2):
            logger.error("This aquarius can cache only encrypted ddos")
            return None
        # always start with MSB -> LSB
        logger.debug(f"checkflags: {check_flags}")
        # bit 2:  check if ddo is ecies encrypted
        if check_flags & 2:
            try:
                rawddo = self.ecies_decrypt(rawddo)
                logger.debug(f"Decrypted to {rawddo}")
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decrypt: {str(err)}")

        # bit 1:  check if ddo is lzma compressed
        if check_flags & 1:
            try:
                rawddo = Lzma.decompress(rawddo)
                logger.debug(f"Decompressed to {rawddo}")
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decompress: {str(err)}")

        logger.debug(f"After unpack rawddo:{rawddo}")
        try:
            ddo = json.loads(rawddo)
            return ddo
        except (KeyError, Exception) as err:
            logger.error(f"encountered an error while decoding the ddo: {str(err)}")
            return None
