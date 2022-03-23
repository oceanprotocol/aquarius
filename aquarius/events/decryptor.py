#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
from datetime import datetime

import requests
from eth_account.messages import encode_defunct
from hashlib import sha256

from aquarius.app.util import get_aquarius_wallet

logger = logging.getLogger(__name__)


def decrypt_ddo(w3, provider_url, contract_address, chain_id, txid, hash):
    aquarius_account = get_aquarius_wallet()
    nonce = str(int(datetime.utcnow().timestamp()))

    signature = aquarius_account.sign_message(
        encode_defunct(text=f"{txid}{aquarius_account.address}{chain_id}{nonce}")
    ).signature.hex()

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
        raise Exception(msg)

    if response.status_code == 201:
        if sha256(response.content).hexdigest() != hash.hex():
            msg = f"Hash check failed: response={response.text}, encoded response={sha256(response.content).hexdigest()}\n metadata hash={hash.hex()}"
            logger.error(msg)
            raise Exception(msg)
        logger.info("Decrypted DDO successfully.")
        return response.json()

    msg = f"Provider exception on decrypt DDO: {response.content}\n provider URL={provider_url}, payload={payload}."
    logger.error(msg)
    raise Exception(msg)
