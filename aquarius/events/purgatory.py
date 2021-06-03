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
        self.list = set()
        self.update_time = None
        self._oceandb = oceandb

        response = requests.get(
            "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
        )

        if response.status_code == requests.codes.ok:
            self.reference_list = {
                (a["did"], a["reason"]) for a in response.json() if a and "did" in a
            }
        else:
            self.reference_list = set()

    def update_existing_assets_data(self):
        for asset in self._oceandb.list():
            did = asset.get("id", None)
            if not did or not did.startswith("did:op:"):
                continue

            purgatory = asset.get("isInPurgatory", "false")
            if not isinstance(purgatory, str):
                purgatory = "true" if purgatory is True else "false"

            asset["isInPurgatory"] = purgatory
            if "purgatoryData" in asset:
                asset.pop("purgatoryData")
            try:
                self._oceandb.update(json.dumps(asset), did)
            except Exception as e:
                logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    def update_list(self):
        now = int(datetime.now().timestamp())
        if self._purgatory_update_time and (now - self._purgatory_update_time) < 3600:
            return

        self._purgatory_update_time = now
        bad_list = self.reference_list
        if not bad_list:
            return

        if self._purgatory_list == bad_list:
            return

        new_ids = bad_list.difference(self._purgatory_list)
        self._purgatory_list = bad_list
        for _id, reason in new_ids:
            try:
                asset = self._oceandb.read(_id)
                asset["isInPurgatory"] = "true"
                if "purgatoryData" in asset:
                    asset.pop("purgatoryData")

                self._oceandb.update(json.dumps(asset), _id)

            except Exception:
                pass
