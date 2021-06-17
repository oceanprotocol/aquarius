#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from web3 import Web3
from datetime import datetime, timedelta

from tests.helpers import (
    get_web3,
    test_account1,
    send_create_update_tx,
    get_ddo,
    new_ddo,
)
from aquarius.events.purgatory import Purgatory
from freezegun import freeze_time


class PurgatoryForTesting(Purgatory):
    def __init__(self, oceandb):
        self.current_test_asset_list = set()
        self.current_test_account_list = set()
        super(PurgatoryForTesting, self).__init__(oceandb)

    def retrieve_new_list(self, env_var):
        return (
            self.current_test_asset_list
            if env_var == "ASSET_PURGATORY_URL"
            else self.current_test_account_list
        )


def publish_ddo(client, base_ddo_url, events_object):
    ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = ddo.id
    data = Web3.toBytes(text=json.dumps(dict(ddo)))
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()

    return did


def test_purgatory_with_assets(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )
    monkeypatch.setenv(
        "ACCOUNT_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = PurgatoryForTesting(events_object._oceandb)
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"

    purgatory.current_test_asset_list = {(did, "test_reason")}
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # remove did from purgatory, but before 1h passed (won't have an effect)
    purgatory.current_test_asset_list = set()
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # simulate the passage of time (1 hour until next purgatory update)
    in_one_hour = datetime.now() + timedelta(hours=1)
    freezer = freeze_time(in_one_hour)
    freezer.start()

    # this time, removing the did from purgatory will take effect
    purgatory.update_lists()
    freezer.stop()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"


def test_purgatory_with_accounts(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )
    monkeypatch.setenv(
        "ACCOUNT_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = PurgatoryForTesting(events_object._oceandb)
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"

    acc_id = events_object._oceandb.read(did)["event"]["from"]
    purgatory.current_test_account_list = {(acc_id, "test_reason")}
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # remove account from purgatory, but before 1h passed (won't have an effect)
    purgatory.current_test_account_list = set()
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # simulate the passage of time (1 hour until next purgatory update)
    in_one_hour = datetime.now() + timedelta(hours=1)
    freezer = freeze_time(in_one_hour)
    freezer.start()

    # this time, removing the account from purgatory will take effect
    purgatory.update_lists()
    freezer.stop()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"
