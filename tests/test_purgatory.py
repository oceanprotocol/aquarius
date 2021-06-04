#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from web3 import Web3

from tests.helpers import (
    get_web3,
    test_account1,
    send_create_update_tx,
    get_ddo,
    new_ddo,
)
from aquarius.events.purgatory import Purgatory


class TestPurgatory(Purgatory):
    def __init__(self, oceandb):
        self.current_test_list = set()
        super(TestPurgatory, self).__init__(oceandb)

    def retrieve_new_list(self):
        return self.current_test_list


def test_publish(client, base_ddo_url, events_object):
    ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = ddo.id
    data = Web3.toBytes(text=json.dumps(dict(ddo)))
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)

    purgatory = TestPurgatory(events_object._oceandb)
    purgatory.init_existing_assets()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "false"

    purgatory.current_test_list = {(did, "test_reason")}
    purgatory.update_list()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["isInPurgatory"] == "true"
