#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class Purgatory:
    def __init__(self, oceandb):
        self.update_time = None
        self._oceandb = oceandb
        self.reference_asset_list = self.retrieve_new_list("ASSET_PURGATORY_URL")
        self.reference_account_list = self.retrieve_new_list("ACCOUNT_PURGATORY_URL")

    def retrieve_new_list(self, env_var):
        response = requests.get(os.getenv(env_var))

        if response.status_code == requests.codes.ok:
            return {
                (a["did"].lower(), a["reason"])
                for a in response.json()
                if a and "did" in a
            }

        return set()

    def init_existing_assets(self):
        for asset in self._oceandb.list():
            did = asset.get("id", None)
            if not did or not did.startswith("did:op:"):
                continue

            purgatory_dids = [x[0] for x in self.reference_asset_list]
            purgatory_accounts = [x[0] for x in self.reference_account_list]

            purgatory_value = str(
                did.lower() in purgatory_dids
                or asset["event"]["from"] in purgatory_accounts
            ).lower()

            if purgatory_value != asset.get("isInPurgatory"):
                self.update_asset_purgatory_status(asset, purgatory_value)

    def update_asset_purgatory_status(self, asset, purgatory="true"):
        did = asset["id"]
        asset["isInPurgatory"] = purgatory
        try:
            self._oceandb.update(json.dumps(asset), did)
        except Exception as e:
            logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    def get_assets_authored_by(self, account_address):
        body = {
            "query": {
                "query_string": {
                    "query": account_address,
                    "default_field": "event.from",
                }
            }
        }
        page = self._oceandb.driver.es.search(
            index=self._oceandb.driver.db_index, body=body
        )
        total = page["hits"]["total"]
        body["size"] = total
        page = self._oceandb.driver.es.search(
            index=self._oceandb.driver.db_index, body=body
        )

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        return object_list

    def update_lists(self):
        now = int(datetime.now().timestamp())
        if self.update_time and (now - self.update_time) < 3600:
            return

        self.update_time = now

        new_asset_list = self.retrieve_new_list("ASSET_PURGATORY_URL")
        new_ids_for_purgatory = new_asset_list.difference(self.reference_asset_list)
        new_ids_forgiven = self.reference_asset_list.difference(new_asset_list)

        new_account_list = self.retrieve_new_list("ACCOUNT_PURGATORY_URL")
        new_accounts_for_purgatory = new_account_list.difference(
            self.reference_account_list
        )
        new_accounts_forgiven = self.reference_account_list.difference(new_account_list)

        self.reference_asset_list = new_asset_list
        self.reference_account_list = new_account_list

        for did, reason in new_ids_for_purgatory:
            asset = self._oceandb.read(did)
            self.update_asset_purgatory_status(asset)

        for did, reason in new_ids_forgiven:
            asset = self._oceandb.read(did)
            self.update_asset_purgatory_status(asset, "false")

        for acc_id, reason in new_accounts_for_purgatory:
            assets = self.get_assets_authored_by(acc_id)
            for asset in assets:
                self.update_asset_purgatory_status(asset)

        for acc_id, reason in new_accounts_forgiven:
            assets = self.get_assets_authored_by(acc_id)
            for asset in assets:
                self.update_asset_purgatory_status(asset, "false")
