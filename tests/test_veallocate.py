#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from freezegun import freeze_time
from requests.models import Response

from aquarius.events.ve_allocate import VeAllocate
from tests.helpers import get_ddo, publish_ddo


class VeAllocateForTesting(VeAllocate):
    def __init__(self, es_instance):
        self.current_test_asset_list = set()
        super(VeAllocateForTesting, self).__init__(es_instance)

    def retrieve_new_list(self, env_var):
        return self.current_test_asset_list if env_var == "VEALLOCATE_URL" else None


def test_ve_allocate_with_assets(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "VEALLOCATE_URL",
        "https://test-df-sql.oceandao.org/nftinfo",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    veAllocate = VeAllocateForTesting(events_object._es_instance)
    published_ddo = get_ddo(client, base_ddo_url, did)

    veAllocate.current_test_asset_list = {
        (published_ddo["nftAddress"], 100, published_ddo["chainId"])
    }
    veAllocate.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["stats"]["allocated"] == 100
