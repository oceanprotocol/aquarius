#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from datetime import datetime

import elasticsearch
import requests

logger = logging.getLogger(__name__)


class Purgatory:
    def __init__(self, es_instance):
        self.update_time = None
        self._es_instance = es_instance
        self.reference_asset_list = set()
        self.reference_account_list = set()

    def retrieve_new_list(self, env_var):
        """
        :param env_var: Url of the file containing purgatory list.
        :return: Object as follows: {...('<did>', '<reason>'),...}
        """
        response = requests.get(os.getenv(env_var), timeout=5)

        if response.status_code == requests.codes.ok:
            logger.info(
                f"PURGATORY: Successfully retrieved new purgatory list from {env_var} env var."
            )
            return {
                (a["did"], a["reason"]) for a in response.json() if a and "did" in a
            }

        logger.info(
            f"PURGATORY: Failed to retrieve purgatory list from {env_var} env var."
        )
        return set()

    def update_asset_purgatory_status(self, asset, purgatory=True, reason=""):
        """
        Updates the fields `state` and `reason` of field `purgatory` in `asset` object.
        """
        did = asset["id"]
        if "purgatory" not in asset:
            asset["purgatory"] = {}

        asset["purgatory"]["state"] = purgatory
        asset["purgatory"]["reason"] = reason
        logger.info(f"PURGATORY: updating asset {did} with value {purgatory}.")
        try:
            self._es_instance.update(json.dumps(asset), did)
        except Exception as e:
            logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    def get_assets_authored_by(self, account_address):
        """
        :return: List of assets authored by `account_address`
        """
        logger.info(f"PURGATORY: getting assets authored by {account_address}.")
        query = {
            "query_string": {
                "query": account_address,
                "default_field": "event.from",
            }
        }

        page = self._es_instance.es.search(
            index=self._es_instance.db_index, query=query
        )
        total = page["hits"]["total"]["value"]
        page = self._es_instance.es.search(
            index=self._es_instance.db_index, query=query, size=total
        )

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        return object_list

    def update_lists(self):
        """
        :return: None
        """
        now = int(datetime.now().timestamp())
        req_diff = int(os.getenv("PURGATORY_UPDATE_INTERVAL", "60")) * 60
        if self.update_time and (now - self.update_time) < req_diff:
            return

        logger.info(
            f"PURGATORY: updating purgatory list and setting update time to {now}."
        )
        self.update_time = now

        new_asset_list = self.retrieve_new_list("ASSET_PURGATORY_URL")
        new_ids_for_purgatory = new_asset_list.difference(self.reference_asset_list)
        new_ids_forgiven = self.reference_asset_list.difference(new_asset_list)

        new_account_list = self.retrieve_new_list("ACCOUNT_PURGATORY_URL")
        new_accounts_for_purgatory = new_account_list.difference(
            self.reference_account_list
        )
        new_accounts_forgiven = self.reference_account_list.difference(new_account_list)

        for acc_id, reason in new_accounts_for_purgatory:
            assets = self.get_assets_authored_by(acc_id)
            for asset in assets:
                self.update_asset_purgatory_status(asset, reason=reason)
            self.reference_account_list.add((acc_id, reason))

        for acc_id, reason in new_accounts_forgiven:
            assets = self.get_assets_authored_by(acc_id)
            for asset in assets:
                self.update_asset_purgatory_status(asset, False, reason)
            self.reference_account_list.remove((acc_id, reason))

        for did, reason in new_ids_for_purgatory:
            try:
                asset = self._es_instance.read(did)
                self.update_asset_purgatory_status(asset, reason=reason)
                self.reference_asset_list.add((did, reason))
            except elasticsearch.exceptions.NotFoundError:
                continue

        for did, reason in new_ids_forgiven:
            try:
                asset = self._es_instance.read(did)
                self.update_asset_purgatory_status(asset, False, reason)
                self.reference_asset_list.remove((did, reason))
            except elasticsearch.exceptions.NotFoundError:
                continue

        logger.info(
            f"PURGATORY: reference asset list contains {len(self.reference_asset_list)} elements."
        )

        logger.info(
            f"PURGATORY: reference account list contains {len(self.reference_account_list)} elements."
        )

    def is_account_banned(self, ref_account_id):
        """
        :return: True if `ref_account_id` is in the Purgatory list.
        """
        for acc_id, reason in self.reference_account_list:
            if acc_id.lower() == ref_account_id.lower():
                return True

        return False
