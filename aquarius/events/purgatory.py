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
                (a["did"], a["reason"]) for a in response.json() if a and "did" in a
            }

        return set()

    def init_existing_assets(self):
        for asset in self._oceandb.list():
            did = asset.get("id", None)
            if not did or not did.startswith("did:op:"):
                continue

            purgatory_value = str(
                did in [x[0] for x in self.reference_asset_list]
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

    def update_lists(self):
        now = int(datetime.now().timestamp())
        if self.update_time and (now - self.update_time) < 3600:
            return

        self.update_time = now

        new_asset_list = self.retrieve_new_list("ASSET_PURGATORY_URL")
        new_ids_for_purgatory = new_asset_list.difference(self.reference_asset_list)
        new_ids_forgiven = self.reference_asset_list.difference(new_asset_list)

        self.reference_asset_list = new_asset_list

        for did, reason in new_ids_for_purgatory:
            asset = self._oceandb.read(did)
            self.update_asset_purgatory_status(asset)

        for did, reason in new_ids_forgiven:
            asset = self._oceandb.read(did)
            self.update_asset_purgatory_status(asset, "false")
