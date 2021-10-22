#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from eth_account import Account
from eth_account.messages import encode_defunct
import os
import requests


def decrypt_ddo(w3, provider_url, contract_address, chain_id, txid):
    aquarius_account = Account.from_key(os.environ.get("PRIVATE_KEY"))
    signature = get_signature(w3, provider_url, aquarius_account)

    response = requests.post(
        provider_url + '/api/v1/services/decryptDDO',
        json={
            "transactionId": txid,
            "chainId": chain_id,
            "dataNftAddress": contract_address,
            "decrypterAddress": aquarius_account.address,
            "signature": signature
        }
    )
    import pdb; pdb.set_trace()


def get_signature(w3, provider_url, account):
    response = requests.get(
        provider_url + '/api/v1/services/nonce',
        params={"userAddress": account.address}
    )
    nonce = response.json()["nonce"]
    return account.sign_message(encode_defunct(text=f"{account.address}{nonce}")).signature.hex()

