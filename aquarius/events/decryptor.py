#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os

import requests
from eth_account import Account
from eth_account.messages import encode_defunct


def decrypt_ddo(w3, provider_url, contract_address, chain_id, txid):
    aquarius_account = Account.from_key(os.environ.get("PRIVATE_KEY"))
    nonce, signature = get_nonce_and_signature(
        w3, provider_url, aquarius_account, txid, chain_id
    )
    payload = {
        "transactionId": txid,
        "chainId": chain_id,
        "decrypterAddress": aquarius_account.address,
        "signature": signature,
        "nonce": nonce,
    }

    response = requests.post(provider_url + "/api/services/decrypt", json=payload)
    if response.status_code == 201:
        return response.json()

    raise Exception(f"Provider exception on decrypt DDO: {response.content}")


def get_nonce_and_signature(w3, provider_url, account, txid, chain_id):
    response = requests.get(
        provider_url + "/api/services/nonce", params={"userAddress": account.address}
    )
    if response.status_code == 200:
        nonce = response.json()["nonce"]
        return (
            nonce,
            account.sign_message(
                encode_defunct(text=f"{txid}{account.address}{chain_id}{nonce}")
            ).signature.hex(),
        )

    raise Exception(f"Provider exception on nonce retrieval: {response.content}")
