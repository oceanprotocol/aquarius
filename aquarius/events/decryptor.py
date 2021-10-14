#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import lzma as Lzma

from aquarius.app.util import get_bool_env_value

logger = logging.getLogger(__name__)


class Decryptor:
    def decode_ddo(self, rawddo, flags):
        # TODO
        if len(flags) < 1:
            logger.debug("Set check_flags to 0!")
            check_flags = 0
        else:
            check_flags = flags[0]

        _only_encrypted_ddo = get_bool_env_value("ONLY_ENCRYPTED_DDO", 0)
        if _only_encrypted_ddo and (not check_flags & 2):
            logger.error("This aquarius can cache only encrypted ddos")
            return None

        if not rawddo:
            logger.error("The rawddo is empty. Can not decrypt or decompress.")
            return None

        # always start with MSB -> LSB
        # bit 2:  check if ddo is ecies encrypted

        if check_flags & 2:
            try:
                rawddo = self.ecies_decrypt(rawddo)
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decrypt: {str(err)}")

        # bit 1:  check if ddo is lzma compressed
        if check_flags & 1:
            try:
                rawddo = Lzma.decompress(rawddo)
            except (KeyError, Exception) as err:
                logger.error(f"Failed to decompress: {str(err)}")

        try:
            ddo = json.loads(rawddo)
            return ddo
        except (KeyError, Exception) as err:
            logger.error(
                f"encountered an error({str(err)}) while decoding the ddo: {rawddo}"
            )
            return None
