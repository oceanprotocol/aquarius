#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from web3.datastructures import AttributeDict

from aquarius.events.proof_checker import check_metadata_proofs
from aquarius.myapp import app
from aquarius.events.util import setup_web3


def test_check_metadata_proofs(monkeypatch):
    # empty env var => everything is validated
    monkeypatch.delenv("ALLOWED_VALIDATORS", None)
    assert check_metadata_proofs(None, "whatever_it_works")

    # wrong env var => nothing is validated
    monkeypatch.setenv("ALLOWED_VALIDATORS", "not a json")
    assert not check_metadata_proofs(None, "whatever_it_works")

    web3 = setup_web3()

    random_addresses = []
    random_dicts = []

    for i in range(5):
        random_address = web3.eth.account.create().address
        random_addresses.append(random_address)
        random_dicts.append(
            AttributeDict({"args": AttributeDict({"validator": random_address})})
        )

    monkeypatch.setenv(
        "ALLOWED_VALIDATORS", json.dumps([random_addresses[0], random_addresses[1]])
    )
    assert check_metadata_proofs(web3, [random_dicts[0]])
    assert check_metadata_proofs(web3, [random_dicts[1]])
    assert not check_metadata_proofs(web3, [random_dicts[2]])
    assert not check_metadata_proofs(web3, [random_dicts[2], random_dicts[3]])
    assert check_metadata_proofs(web3, [random_dicts[0], random_dicts[3]])
    assert check_metadata_proofs(web3, [random_dicts[0], random_dicts[0]])

    # no metadata proofs set
    assert not check_metadata_proofs(web3, [])
    assert not check_metadata_proofs(web3, [])

    # no validators set
    monkeypatch.setenv("ALLOWED_VALIDATORS", json.dumps([]))
    assert check_metadata_proofs(web3, [random_dicts[4]])
