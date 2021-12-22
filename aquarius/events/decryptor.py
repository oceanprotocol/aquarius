#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime
import os

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from hashlib import sha256


def decrypt_ddo(w3, provider_url, contract_address, chain_id, txid, hash):
    pk = os.environ.get("PRIVATE_KEY", None)
    if pk is None:
        raise Exception("Missing Aquarius PRIVATE_KEY")

    aquarius_account = Account.from_key(pk)
    nonce = str(datetime.now().timestamp())
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
