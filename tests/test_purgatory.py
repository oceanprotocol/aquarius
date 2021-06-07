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


class TestPurgatory(Purgatory):
    def __init__(self, oceandb):
        self.current_test_list = set()
        super(TestPurgatory, self).__init__(oceandb)

    def retrieve_new_list(self):
        return self.current_test_list


def publish_ddo(client, base_ddo_url, events_object):
    ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = ddo.id
    data = Web3.toBytes(text=json.dumps(dict(ddo)))
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()

    return did


def test_update_list(client, base_ddo_url, events_object):
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = TestPurgatory(events_object._oceandb)
    purgatory.init_existing_assets()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"

    purgatory.current_test_list = {(did, "test_reason")}
    purgatory.update_list()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # remove did from purgatory, but before 1h passed (won't have an effect)
    purgatory.current_test_list = set()
    purgatory.update_list()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"

    # simulate the passage of time (1 hour until next purgatory update)
    in_one_hour = datetime.now() + timedelta(hours=1)
    freezer = freeze_time(in_one_hour)
    freezer.start()

    # this time, removing the did from purgatory will take effect
    purgatory.update_list()
    freezer.stop()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"
