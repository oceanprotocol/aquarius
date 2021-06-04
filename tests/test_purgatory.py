#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import uuid
from web3 import Web3

from aquarius.events.util import deploy_datatoken
from eth_utils import remove_0x_prefix

from tests.helpers import get_web3, test_account1, send_create_update_tx, get_ddo
from tests.ddos.ddo_event_sample import ddo_event_sample
from aquarius.events.purgatory import Purgatory
from web3.datastructures import AttributeDict


def new_ddo_purgatory(account, web3, name, ddo=None):
    _ddo = ddo if ddo else ddo_event_sample.copy()
    if "publicKey" not in _ddo or not _ddo["publicKey"]:
        _ddo["publicKey"] = [{"owner": ""}]
    _ddo["publicKey"][0]["owner"] = account.address
    _ddo["random"] = str(uuid.uuid4())
    dt_address = deploy_datatoken(web3, account.privateKey, name, name, account.address)
    _ddo["id"] = f"did:op:{remove_0x_prefix(dt_address)}"
    _ddo["dataToken"] = dt_address
    return AttributeDict(_ddo)


def test_publish(client, base_ddo_url, events_object):
    _ddo = new_ddo_purgatory(test_account1, get_web3(), "dt.0")
    did = _ddo.id
    ddo_string = json.dumps(dict(_ddo))
    data = Web3.toBytes(text=ddo_string)
    send_create_update_tx("create", did, bytes([0]), data, test_account1)
    events_object.process_current_blocks()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["id"] == did
    purgatory = Purgatory(events_object._oceandb)
    purgatory.init_existing_assets()
    purgatory.update_list()
