#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime

import requests
from eth_account.messages import encode_defunct
from hashlib import sha256

from aquarius.app.util import get_aquarius_wallet


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
        "signature": signature,
        "nonce": nonce,
    }

    response = requests.post(provider_url + "/api/services/decrypt", json=payload)

    if response.status_code == 201:
        if sha256(response.text.encode("utf-8")).hexdigest() != hash.hex():
            raise Exception(f"Hash check failed")
        return response.json()

    raise Exception(f"Provider exception on decrypt DDO: {response.content}")
