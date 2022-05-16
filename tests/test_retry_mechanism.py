#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime, timedelta
from freezegun import freeze_time
import os

from aquarius.retry_mechanism import RetryMechanism


def test_add_get(client, base_ddo_url, events_object, monkeypatch):
    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    mechanism = RetryMechanism(
        config_file,
        events_object._es_instance,
        events_object._retries_db_index,
        None
    )
    mechanism.clear_all()

    random_address = mechanism._web3.eth.account.create().key.hex()

    now = datetime.utcnow()
    freezer = freeze_time(now)
    freezer.start()

    mechanism.add_to_retry_queue(random_address, 0, 1337)

    tx_ids = [res["_source"]["tx_id"] for res in mechanism.get_from_retry_queue()]
    assert random_address not in tx_ids

    freezer.stop()

    after_5_minutes_and_a_bit = now + timedelta(minutes=5, seconds=1)
    freezer = freeze_time(after_5_minutes_and_a_bit)
    freezer.start()

    tx_ids = [res["_source"]["tx_id"] for res in mechanism.get_from_retry_queue()]
    assert random_address in tx_ids

    freezer.stop()

