#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
from datetime import datetime
from hashlib import sha256

import requests

from aquarius.app.util import get_aquarius_wallet, get_signature_bytes

logger = logging.getLogger(__name__)


def decrypt_ddo(w3, provider_url, contract_address, chain_id, txid, hash):
    aquarius_account = get_aquarius_wallet()
    nonce = str(int(datetime.utcnow().timestamp()))

    signature = get_signature_bytes(
        f"{txid}{aquarius_account.address}{chain_id}{nonce}"
    )
    payload = {
        "transactionId": txid,
        "chainId": chain_id,
        "decrypterAddress": aquarius_account.address,
        "dataNftAddress": contract_address,
        "signature": signature,
        "nonce": nonce,
    }

    response = requests.post(provider_url + "/api/services/decrypt", json=payload)

    if not response or not hasattr(response, "status_code"):
        msg = f"Failed to get a response for decrypt DDO with provider={provider_url}, payload={payload}, response is {response.content}"
        logger.error(msg)
        raise Exception(f"in decrypt_ddo: {msg}")

    if response.status_code == 201:
        if sha256(response.content).hexdigest() != hash.hex():
            msg = f"Hash check failed: response={response.content}, encoded response={sha256(response.content).hexdigest()}\n metadata hash={hash.hex()}"
            logger.error(msg)
            raise Exception(f"in decrypt_ddo: {msg}")
        logger.info("Decrypted DDO successfully.")
        response_content = response.content.decode("utf-8")

        return json.loads(response_content)

    if response.status_code == 403:
        # unauthorised decrypter
        return False

    msg = f"Provider exception on decrypt DDO: {response.content}\n provider URL={provider_url}, payload={payload}."
    logger.error(msg)
    raise Exception(f"in decrypt_ddo: {msg}")
