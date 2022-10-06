#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from freezegun import freeze_time
from requests.models import Response

from aquarius.events.veAllocate import VeAllocate
from tests.helpers import (
    get_ddo,
    get_web3,
    new_ddo,
    send_create_update_tx,
    test_account1,
)


class VeAllocateForTesting(VeAllocate):
    def __init__(self, es_instance):
        self.current_test_asset_list = set()
        super(VeAllocateForTesting, self).__init__(es_instance)

    def retrieve_new_list(self, env_var):
        return self.current_test_asset_list if env_var == "VEALLOCATE_URL" else None


def publish_ddo(client, base_ddo_url, events_object):
    ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = ddo.id
    send_create_update_tx("create", ddo, bytes([0]), test_account1)
    events_object.process_current_blocks()

    return did


def test_ve_allocate_with_assets(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "VEALLOCATE_URL",
        "https://test-df-sql.oceandao.org/nftinfo",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = VeAllocateForTesting(events_object._es_instance)
    published_ddo = get_ddo(client, base_ddo_url, did)

    purgatory.current_test_asset_list = {
        (published_ddo["nftAddress"], 100, published_ddo["chainId"])
    }
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["allocated"] == 100
