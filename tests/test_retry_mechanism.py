#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import timedelta
import os
import time

from aquarius.retry_mechanism import RetryMechanism


def test_add_get(client, base_ddo_url, events_object, monkeypatch):
    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    mechanism = RetryMechanism(
        config_file,
        events_object._es_instance,
        events_object._retries_db_index,
        None
    )
    mechanism.retry_interval = timedelta(seconds=10)

    random_address = mechanism._web3.eth.account.create().key.hex()
    mechanism.add_to_retry_queue(random_address, 0, 1337)

    tx_ids = [res["_source"]["tx_id"] for res in mechanism.get_from_retry_queue()]
    assert random_address not in tx_ids
    time.sleep(11)
    tx_ids = [res["_source"]["tx_id"] for res in mechanism.get_from_retry_queue()]
    import pdb; pdb.set_trace()
    assert random_address in tx_ids

