#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import Mock, patch

from freezegun import freeze_time
from datetime import datetime, timedelta
from requests.models import Response

from aquarius.events.purgatory import Purgatory
from tests.helpers import get_ddo, publish_ddo


class PurgatoryForTesting(Purgatory):
    def __init__(self, es_instance):
        self.current_test_asset_list = set()
        self.current_test_account_list = set()
        super(PurgatoryForTesting, self).__init__(es_instance)

    def retrieve_new_list(self, env_var):
        return (
            self.current_test_asset_list
            if env_var == "ASSET_PURGATORY_URL"
            else self.current_test_account_list
        )


def test_purgatory_before_init(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )

    purgatory = PurgatoryForTesting(events_object._es_instance)
    purgatory.current_test_asset_list = {("did:op:notexistyet", "test_reason")}
    purgatory.update_lists()
    # assert no change, since this did doesn't exist
    assert purgatory.reference_asset_list == set()


def test_purgatory_with_assets(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )
    monkeypatch.setenv(
        "ACCOUNT_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = PurgatoryForTesting(events_object._es_instance)
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is False

    purgatory.current_test_asset_list = {(did, "test_reason")}
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is True

    # remove did from purgatory, but before 1h passed (won't have an effect)
    purgatory.current_test_asset_list = set()
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is True

    # simulate the passage of time (1 hour until next purgatory update)
    in_one_hour = datetime.now() + timedelta(hours=1)
    freezer = freeze_time(in_one_hour)
    freezer.start()

    # this time, removing the did from purgatory will take effect
    purgatory.update_lists()
    freezer.stop()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is False


def test_purgatory_with_accounts(client, base_ddo_url, events_object, monkeypatch):
    monkeypatch.setenv(
        "ASSET_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json",
    )
    monkeypatch.setenv(
        "ACCOUNT_PURGATORY_URL",
        "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json",
    )
    did = publish_ddo(client, base_ddo_url, events_object)

    purgatory = PurgatoryForTesting(events_object._es_instance)
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is False

    acc_id = events_object._es_instance.read(did)["event"]["from"]
    purgatory.current_test_account_list = {(acc_id, "test_reason")}
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is True

    # remove account from purgatory, but before 1h passed (won't have an effect)
    purgatory.current_test_account_list = set()
    purgatory.update_lists()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is True

    # simulate the passage of time (1 hour until next purgatory update)
    in_one_hour = datetime.now() + timedelta(hours=1)
    freezer = freeze_time(in_one_hour)
    freezer.start()

    # this time, removing the account from purgatory will take effect
    purgatory.update_lists()
    freezer.stop()
    published_ddo = get_ddo(client, base_ddo_url, did)
    assert published_ddo["purgatory"]["state"] is False


def test_purgatory_retrieve_new_list(events_object):
    purgatory = Purgatory(events_object._es_instance)
    with patch("requests.get") as mock:
        the_response = Mock(spec=Response)
        the_response.status_code = 200
        the_response.json.return_value = [{"did": "some_did", "reason": "some_reason"}]
        mock.return_value = the_response
        assert purgatory.retrieve_new_list("env") == {("some_did", "some_reason")}

    with patch("requests.get") as mock:
        the_response = Mock(spec=Response)
        the_response.status_code = 400
        mock.return_value = the_response
        assert purgatory.retrieve_new_list("env") == set()


def test_failures(events_object):
    purgatory = Purgatory(events_object._es_instance)
    with patch("aquarius.app.es_instance.ElasticsearchInstance.update") as mock:
        mock.side_effect = Exception("Boom!")
        purgatory.update_asset_purgatory_status({"id": "id", "stats": {}})


def test_is_account_banned(events_object):
    purgatory = Purgatory(events_object._es_instance)
    purgatory.reference_account_list = {("0x123AbC", "bad juju")}
    assert purgatory.is_account_banned("0x123abc")  # capitalization doesn't matter
    assert not purgatory.is_account_banned("some_other_value")
