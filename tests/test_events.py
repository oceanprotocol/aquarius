#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
from unittest.mock import patch

from jsonsempai import magic  # noqa: F401
from artifacts import ERC20Template
import elasticsearch

from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.util import setup_web3
from aquarius.myapp import app
from tests.helpers import (
    get_ddo,
    get_web3,
    new_ddo,
    send_create_update_tx,
    send_set_metadata_state_tx,
    test_account1,
    test_account3,
)


def run_test(client, base_ddo_url, events_instance, flags):
    web3 = events_instance._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, _, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([flags]), test_account1
    )
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    for service in published_ddo["services"]:
        assert service["datatokenAddress"] == erc20_address

    _ddo["metadata"]["name"] = "Updated ddo by event"
    send_create_update_tx("update", _ddo, bytes([flags]), test_account1)
    events_instance.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["metadata"]["name"] == "Updated ddo by event"


def test_publish_and_update_ddo(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 2)


def test_publish_and_update_ddo_with_lzma(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 1)


def test_publish_and_update_ddo_with_lzma_and_encrypt(
    client, base_ddo_url, events_object
):
    run_test(client, base_ddo_url, events_object, 3)


def test_publish_and_update_ddo_unencrypted(client, base_ddo_url, events_object):
    run_test(client, base_ddo_url, events_object, 0)


def test_publish(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    send_create_update_tx("create", _ddo, bytes([2]), test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    assert published_ddo["chainId"] == get_web3().eth.chain_id


def test_publish_unallowed_address(client, base_ddo_url, events_object):
    _ddo = new_ddo(test_account3, get_web3(), "dt.0")
    did = _ddo.id
    send_create_update_tx("create", _ddo, bytes([2]), test_account3)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["error"] == f"Asset DID {did} not found in Elasticsearch."


def test_publish_and_update_ddo_rbac(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv("RBAC_SERVER_URL", "http://localhost:3000")
    run_test(client, base_ddo_url, events_object, 2)


def test_get_chains_list(client, chains_url):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    rv = client.get(chains_url + "/list", content_type="application/json")
    chains_list = json.loads(rv.data.decode("utf-8"))
    assert chains_list
    assert chains_list[str(chain_id)]


def test_get_chain_status(client, chains_url):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    rv = client.get(
        chains_url + f"/status/{str(chain_id)}", content_type="application/json"
    )
    chain_status = json.loads(rv.data.decode("utf-8"))
    assert int(chain_status["last_block"]) > 0


def test_get_assets_in_chain(client, events_object):
    web3_object = get_web3()
    chain_id = web3_object.eth.chain_id
    res = events_object.get_assets_in_chain()
    assert set([item["chainId"] for item in res]) == {chain_id}


def test_events_monitor_object(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monkeypatch.setenv("ALLOWED_PUBLISHERS", "can not be converted to a set")
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor._allowed_publishers == set()

    monkeypatch.setenv("OCN_EVENTS_MONITOR_QUITE_TIME", "can not be converted to int")
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor._monitor_sleep_time == 10

    monkeypatch.setenv("EVENTS_CLEAN_START", "1")
    with patch("aquarius.events.events_monitor.EventsMonitor.reset_chain") as mock:
        monitor = EventsMonitor(setup_web3(config_file), config_file)
        mock.assert_called_once()


def test_start_stop_events_monitor():
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)

    monitor._monitor_is_on = True
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor._contract_address = None
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor._contract = None
    assert monitor.start_events_monitor() is None

    monitor = EventsMonitor(setup_web3(config_file), config_file)
    with patch("aquarius.events.events_monitor.Thread.start") as mock:
        monitor.start_events_monitor()
        mock.assert_called_once()

    monitor.stop_monitor()


def test_run_monitor(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor.sleep_time = 1

    monitor._monitor_is_on = False
    assert monitor.do_run_monitor() is None

    monitor._monitor_is_on = True
    with patch(
        "aquarius.events.events_monitor.EventsMonitor.process_current_blocks"
    ) as mock:
        mock.side_effect = Exception("Boom!")
        assert monitor.do_run_monitor() is None

    with patch(
        "aquarius.events.events_monitor.EventsMonitor.process_current_blocks"
    ) as mock:
        monitor.do_run_monitor()
        mock.assert_called_once()


def test_run_monitor_purgatory(monkeypatch):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor._monitor_is_on = True
    with patch("aquarius.events.purgatory.Purgatory.update_lists") as mock:
        monitor.do_run_monitor()
        mock.assert_called_once()

    with patch("aquarius.events.purgatory.Purgatory.update_lists") as mock:
        mock.side_effect = Exception("Boom!")
        monitor.do_run_monitor()


def test_process_block_range(client, base_ddo_url, events_object):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    assert monitor.process_block_range(13, 10) is None  # not processing if from > to

    _ddo = new_ddo(test_account1, get_web3(), "dt.0")
    send_create_update_tx("create", _ddo, bytes([2]), test_account1)

    with patch(
        "aquarius.events.events_monitor.MetadataCreatedProcessor.process"
    ) as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.process_current_blocks() is None

    send_create_update_tx("update", _ddo, bytes([2]), test_account1)
    with patch(
        "aquarius.events.events_monitor.MetadataUpdatedProcessor.process"
    ) as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.process_current_blocks() is None


def test_get_last_processed_block(events_object):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.get_last_processed_block() == 0

    start_block = events_object._start_block
    intended_block = -10  # can not be smaller than start block
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.return_value = {"last_block": intended_block}
        assert events_object.get_last_processed_block() == start_block


def test_store_last_processed_block(events_object):
    block = events_object.get_last_processed_block() + 10
    with patch("elasticsearch.Elasticsearch.index") as mock:
        mock.side_effect = elasticsearch.exceptions.RequestError("Boom!")
        assert events_object.store_last_processed_block(block) is None


def test_add_chain_id_to_chains_list(events_object):
    with patch("elasticsearch.Elasticsearch.get") as mock:
        mock.side_effect = Exception("Boom!")
        assert events_object.add_chain_id_to_chains_list() is None

    with patch("elasticsearch.Elasticsearch.index") as mock:
        mock.side_effect = elasticsearch.exceptions.RequestError("Boom!")
        events_object.add_chain_id_to_chains_list()
        assert events_object.add_chain_id_to_chains_list() is None


def test_get_event_logs(events_object):
    assert events_object.get_event_logs("NonExistentEvent", 0, 10) == []


def test_order_started(events_object, client, base_ddo_url):
    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    _, dt_contract, erc20_address = send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    token_contract = web3.eth.contract(abi=ERC20Template.abi, address=erc20_address)

    token_contract.functions.mint(
        test_account3.address, web3.toWei(10, "ether")
    ).transact({"from": test_account1.address})
    txn = token_contract.functions.startOrder(
        test_account3.address,
        web3.toWei(1, "ether"),
        1,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        0,
    ).transact({"from": test_account3.address})
    web3.eth.wait_for_transaction_receipt(txn)
    events_object.process_current_blocks()

    published_ddo = get_ddo(client, base_ddo_url, did)
    # TODO: currently the graph for v4 is WIP, need to replace this
    assert published_ddo["stats"]["consumes"] == -1


def test_metadata_state_update(client, base_ddo_url, events_object):

    web3 = events_object._web3  # get_web3()
    block = web3.eth.block_number
    _ddo = new_ddo(test_account1, web3, f"dt.{block}")
    did = _ddo.id

    send_create_update_tx(
        "create", _ddo, bytes([2]), test_account1
    )
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did

    send_set_metadata_state_tx(_ddo, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did