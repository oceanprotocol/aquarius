#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
from eth_account import Account
from aquarius.events.decryptor import Decryptor
from tests.ddos.rawddos import lzma_compressed_sample, ecies_encrypted_sample
from unittest.mock import patch


def test_decode_ddo(events_object, monkeypatch):
    ecies_private_key = os.environ.get("EVENTS_ECIES_PRIVATE_KEY", None)
    ecies_account = Account.from_key(ecies_private_key)
    decryptor = Decryptor(ecies_account)

    monkeypatch.setenv("ONLY_ENCRYPTED_DDO", "1")
    # flags set to 0 by default, can not decrypt if only encrypted DDOs work
    assert decryptor.decode_ddo("some_encrypted_ddo", "") is None
    monkeypatch.setenv("ONLY_ENCRYPTED_DDO", "0")

    # empty ddo
    assert decryptor.decode_ddo(None, "") is None

    # happy path
    result = decryptor.decode_ddo(lzma_compressed_sample, b"\x01")
    assert "@context" in result

    result = decryptor.decode_ddo(ecies_encrypted_sample, b"\x03")
    assert "@context" in result

    # various errors
    with patch("json.loads") as mock:
        mock.side_effect = Exception("Boom!")
        assert decryptor.decode_ddo(ecies_encrypted_sample, b"\x03") is None
    decryptor._ecies_account = "mess up the account to get an error"
    assert decryptor.decode_ddo(ecies_encrypted_sample, b"\x03") is None
    assert (
        decryptor.decode_ddo("some sort of string instead of binary", b"\x03") is None
    )
