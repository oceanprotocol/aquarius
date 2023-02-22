#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json

from aquarius.constants import BaseURLs
from aquarius.events.constants import EventTypes
from tests.ddo_samples_invalid import json_dict_no_valid_metadata
from tests.ddos.ddo_sample1_v4 import json_dict
from tests.helpers import (
    get_web3,
    new_ddo,
    run_request,
    run_request_get_data,
    send_create_update_tx,
    test_account1,
)


def get_ddo(client, base_ddo_url, did):
    rv = client.get(base_ddo_url + f"/{did}", content_type="application/json")
    fetched_ddo = json.loads(rv.data.decode("utf-8"))
    return fetched_ddo


def add_assets(_events_object, name, total=5):
    block = get_web3().eth.block_number
    assets = []
    txs = []
    for i in range(total):
        ddo = new_ddo(test_account1, get_web3(), f"{name}.{i+block}", json_dict)
        assets.append(ddo)

        txs.append(send_create_update_tx("create", ddo, bytes([1]), test_account1)[0])

    # process all new ddo, starting from original block, before the txs
    _events_object.store_last_processed_block(block - 1)
    for ddo in assets:
        _events_object.process_current_blocks()

    return assets


def test_post_with_no_valid_ddo(client, base_ddo_url, events_object):
    block = get_web3().eth.block_number
    ddo = new_ddo(test_account1, get_web3(), f"dt.{block}", json_dict_no_valid_metadata)
    _ = send_create_update_tx("create", ddo, bytes([1]), test_account1)
    events_object.process_current_blocks()
    try:
        published_ddo = get_ddo(client, base_ddo_url, ddo.id)
        assert not published_ddo, (
            "publish should fail, Aquarius validation "
            "should have failed and skipped the "
            f"{EventTypes.EVENT_METADATA_CREATED} event."
        )
    except Exception:
        pass


def test_resolveByDtAddress(client_with_no_data, query_url, events_object):
    client = client_with_no_data
    block = get_web3().eth.block_number
    _ddo = json_dict.copy()
    ddo = new_ddo(test_account1, get_web3(), f"dt.{block}", _ddo)
    did = ddo["id"]
    dt_address = ddo["nftAddress"]
    send_create_update_tx("create", ddo, bytes([1]), test_account1)
    events_object.process_current_blocks()

    result = run_request(
        client.post,
        query_url,
        {
            "query": {
                "query_string": {"query": dt_address, "default_field": "nft.address"}
            }
        },
    )
    result = result.json
    assert len(result["hits"]["hits"]) > 0

    base_url = BaseURLs.BASE_AQUARIUS_URL + "/assets"
    response = client.get(
        base_url + f"/metadata/{did}", content_type="application/json"
    )
    assert response.headers["Content-Type"] == "application/json"
    assert response.status_code == 200


def test_get_assets_names(client, events_object):
    base_url = BaseURLs.BASE_AQUARIUS_URL + "/assets"

    response = run_request(client.post, base_url + "/names", {"notTheDidList": ["a"]})

    assert response.status == "400 BAD REQUEST"

    response = run_request(client.post, base_url + "/names", {"didList": []})

    assert response.status == "400 BAD REQUEST"

    response = run_request(client.post, base_url + "/names", {"didList": "notadict"})

    assert response.status == "400 BAD REQUEST"

    response = run_request(client.post, base_url + "/names", "notadict")

    assert response.status == "400 BAD REQUEST"

    assets = add_assets(events_object, "dt_name", 3)
    dids = [ddo["id"] for ddo in assets]
    did_to_name = run_request_get_data(
        client.post, base_url + "/names", {"didList": dids}
    )
    for did in dids:
        assert did in did_to_name, "did not found in response."
        assert did_to_name[did], "did name not found."


def test_asset_metadata_not_found(client):
    result = run_request(client.get, "api/aquarius/assets/metadata/missing")
    assert result.status == "404 NOT FOUND"
