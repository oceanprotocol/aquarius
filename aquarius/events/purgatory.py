#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class Purgatory:
    def __init__(self, oceandb):
        self.update_time = None
        self._oceandb = oceandb
        self.reference_list = self.retrieve_new_list()

    def retrieve_new_list(self):
        response = requests.get(
            "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
        )

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

            purgatory_value = str(did in [x[0] for x in self.reference_list]).lower()

            if purgatory_value != asset.get("isInPurgatory"):
                self.update_asset_purgatory_status(asset, purgatory_value)

    def update_asset_purgatory_status(self, asset, purgatory="true"):
        did = asset["id"]
        asset["isInPurgatory"] = purgatory
        if "purgatoryData" in asset:
            asset.pop("purgatoryData")
        try:
            self._oceandb.update(json.dumps(asset), did)
        except Exception as e:
            logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    def update_list(self):
        now = int(datetime.now().timestamp())
        if self.update_time and (now - self.update_time) < 3600:
            return

        self.update_time = now
        if not self.reference_list:
            return

        new_list = self.retrieve_new_list()
        new_ids = new_list.difference(self.reference_list)
        self.reference_list = new_list

        for _id, reason in new_ids:
            asset = self._oceandb.read(_id)
            self.update_asset_purgatory_status(self, asset)
