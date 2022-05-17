#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from freezegun import freeze_time
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os

from aquarius.retry_mechanism import RetryMechanism


def test_add_get(client, base_ddo_url, events_object, monkeypatch):
    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    mechanism = RetryMechanism(
        config_file, events_object._es_instance, events_object._retries_db_index, None
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


def test_add_update(client, base_ddo_url, events_object, monkeypatch):
    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    mechanism = RetryMechanism(
        config_file, events_object._es_instance, events_object._retries_db_index, None
    )
    mechanism.clear_all()

    random_address = mechanism._web3.eth.account.create().key.hex()
    params = {"tx_id": random_address, "log_index": 0, "chain_id": 1337}

    rm_id = sha256(json.dumps(params).encode("utf-8")).hexdigest()

    # first time adding it to the queue
    now = datetime.utcnow()
    freezer = freeze_time(now)
    freezer.start()
    mechanism.add_to_retry_queue(random_address, 0, 1337)
    freezer.stop()

    queue_element = mechanism.get_by_id(rm_id)
    assert queue_element["number_retries"] == 0
    assert queue_element["next_retry"] == int((now + timedelta(minutes=5)).timestamp())

    # try adding to the queue again, will increase the number of retries and the interval
    # to 10 minutes (double)
    after_5_minutes_and_a_bit = now + timedelta(minutes=5, seconds=1)
    freezer = freeze_time(after_5_minutes_and_a_bit)
    freezer.start()

    mechanism.add_to_retry_queue(random_address, 0, 1337)

    freezer.stop()
    queue_element = mechanism.get_by_id(rm_id)
    assert queue_element["number_retries"] == 1
    assert queue_element["next_retry"] == int(
        (after_5_minutes_and_a_bit + timedelta(minutes=10)).timestamp()
    )

    # try adding to the queue again, will increase the number of retries and the interval
    # to 15 minutes (double)
    after_another_10_minutes_and_a_bit = now + timedelta(minutes=10, seconds=1)
    freezer = freeze_time(after_another_10_minutes_and_a_bit)
    freezer.start()

    mechanism.add_to_retry_queue(random_address, 0, 1337)

    freezer.stop()
    queue_element = mechanism.get_by_id(rm_id)
    assert queue_element["number_retries"] == 2
    assert queue_element["next_retry"] == int(
        (after_another_10_minutes_and_a_bit + timedelta(minutes=15)).timestamp()
    )

    # try adding to the queue again, but use asap flag should reset everything
    freezer = freeze_time(after_another_10_minutes_and_a_bit)
    freezer.start()

    mechanism.add_to_retry_queue(random_address, 0, 1337, asap=True)

    freezer.stop()
    queue_element = mechanism.get_by_id(rm_id)
    assert queue_element["number_retries"] == 0
    assert queue_element["next_retry"] == int(
        after_another_10_minutes_and_a_bit.timestamp()
    )
