#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from freezegun import freeze_time
from datetime import datetime, timedelta
from hashlib import sha256
import json
import logging
import os
import time
import pytest

from aquarius.events.events_monitor import EventsMonitor
from tests.helpers import (
    get_ddo,
    get_web3,
    new_ddo,
    run_request_get_data,
    send_create_update_tx,
    send_set_metadata_state_tx,
    test_account1,
    test_account2,
    test_account3,
)

logger = logging.getLogger("aquarius")


def test_retry_tx(client, base_ddo_url, events_object, monkeypatch):
    # create a ddo, and add tx to queue
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    txn_receipt, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.retry_mechanism.retry_interval = timedelta(seconds=1)
    events_object.retry_mechanism.max_hold = 1209600
    events_object.retry_mechanism.clear_all()
    element_id = events_object.retry_mechanism.add_tx_to_retry_queue(
        txn_receipt["transactionHash"].hex()
    )
    queue = events_object.retry_mechanism.get_all()
    # make sure that our tx is in queue
    assert len(queue) > 0

    # wait for 2 seconds in order to have element's next_retry < now
    time.sleep(2)
    # process the entire queue
    events_object.retry_mechanism.process_queue()
    time.sleep(1)

    # let's see if we have the ddo
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["chainId"] == get_web3().eth.chain_id
    r = events_object.retry_mechanism.get_by_id(element_id)
    # make sure that our tx is not in queue anymore
    assert r is None
    queue = events_object.retry_mechanism.get_all()
    # make sure that we don't have other error in queue
    assert len(queue) == 0


def test_retry_block(client, base_ddo_url, events_object, monkeypatch):
    # create a ddo, and add block no to queue
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    txn_receipt, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.retry_mechanism.retry_interval = timedelta(seconds=1)
    events_object.retry_mechanism.max_hold = 1209600
    events_object.retry_mechanism.clear_all()
    element_id = events_object.retry_mechanism.add_block_to_retry_queue(
        txn_receipt["blockNumber"]
    )
    queue = events_object.retry_mechanism.get_all()
    # make sure that our tx is in queue
    assert len(queue) > 0

    # wait for 2 seconds in order to have element's next_retry < now
    time.sleep(2)
    # process the entire queue
    events_object.retry_mechanism.process_queue()
    time.sleep(1)

    # let's see if we have the ddo
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["chainId"] == get_web3().eth.chain_id
    r = events_object.retry_mechanism.get_by_id(element_id)
    # make sure that our tx is not in queue anymore
    assert r is None
    queue = events_object.retry_mechanism.get_all()
    # make sure that we don't have other error in queue
    assert len(queue) == 0


def test_retry_event(client, base_ddo_url, events_object, monkeypatch):
    # create a ddo, and add tx to queue
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    txn_receipt, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.retry_mechanism.retry_interval = timedelta(seconds=1)
    events_object.retry_mechanism.max_hold = 1209600
    events_object.retry_mechanism.clear_all()
    element_id = None
    # iterate over tx events and add METADATA_CREATED to retry queue
    for log in txn_receipt["logs"]:
        if (
            log.topics[0].hex()
            == "0x5463569dcc320958360074a9ab27e809e8a6942c394fb151d139b5f7b4ecb1bd"
        ):
            logger.error(log)
            element_id = events_object.retry_mechanism.add_event_to_retry_queue(
                log, None, None
            )
    # make sure that we found the event
    assert element_id
    queue = events_object.retry_mechanism.get_all()
    # make sure that our tx is in queue
    assert len(queue) > 0

    # wait for 2 seconds in order to have element's next_retry < now
    time.sleep(2)
    # process the entire queue
    events_object.retry_mechanism.process_queue()
    time.sleep(1)

    # let's see if we have the ddo
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["chainId"] == get_web3().eth.chain_id
    r = events_object.retry_mechanism.get_by_id(element_id)
    # make sure that our tx is not in queue anymore
    assert r is None
    queue = events_object.retry_mechanism.get_all()
    # make sure that we don't have other error in queue
    assert len(queue) == 0


def test_retry_tx(client, base_ddo_url, events_object, monkeypatch):
    # insert dummy transaction
    events_object.retry_mechanism.retry_interval = timedelta(seconds=1)
    events_object.retry_mechanism.clear_all()
    events_object.retry_mechanism.add_tx_to_retry_queue("0x0000000000")
    queue = events_object.retry_mechanism.get_all()
    # make sure that our tx is in queue
    assert len(queue) > 0
    # set max hold to 1 sec
    events_object.retry_mechanism.max_hold = 1
    # wait for 2 seconds
    time.sleep(2)
    # process the entire queue
    events_object.retry_mechanism.process_queue()
    time.sleep(1)
    queue = events_object.retry_mechanism.get_all()
    # make sure that our tx is not in queue anymore
    assert len(queue) == 0
