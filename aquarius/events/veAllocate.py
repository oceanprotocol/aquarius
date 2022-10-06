#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from datetime import datetime

import elasticsearch
import requests

from aquarius.events.util import make_did

logger = logging.getLogger(__name__)


class VeAllocate:
    def __init__(self, es_instance):
        self.update_time = None
        self._es_instance = es_instance

    def retrieve_new_list(self, env_var):
        """
        :param env_var: Url of the file containing purgatory list.
        :return: Object as follows: {...('<did>', '<reason>'),...}
        """
        response = requests.post(os.getenv(env_var))

        if response.status_code == requests.codes.ok:
            logger.info(
                f"veAllocate: Successfully retrieved list from {env_var} env var."
            )
            return {
                (a["nft_addr"], a["ve_allocated"], a["chainID"])
                for a in response.json()
                if a and "nft_addr" in a and "ve_allocated" in a and "chainID" in a
            }

        logger.info(f"veAllocate: Failed to retrieve list from {env_var} env var.")
        return set()

    def update_asset(self, asset, veAllocated):
        """
        Updates the field `state.allocated`  in `asset` object.
        """
        did = asset["id"]
        if "stats" not in asset:
            asset["stats"] = {}

        asset["stats"]["allocated"] = veAllocated
        logger.info(
            f"veAllocate: updating asset {did} with state.allocated={veAllocated}."
        )
        try:
            self._es_instance.update(json.dumps(asset), did)
        except Exception as e:
            logger.warning(f"updating ddo {did} purgatory attribute failed: {e}")

    def update_lists(self):
        """
        :return: None
        """
        now = int(datetime.now().timestamp())
        req_diff = int(os.getenv("VEALLOCATE_UPDATE_INTERVAL", "60")) * 60
        if self.update_time and (now - self.update_time) < req_diff:
            return

        logger.info(
            f"veAllocate: updating veAllocate list and setting update time to {now}."
        )
        self.update_time = now

        ve_list = self.retrieve_new_list("VEALLOCATE_URL")

        for nft, ve_allocated, chainID in ve_list:
            try:
                did = make_did(nft, chainID)
                asset = self._es_instance.read(did)
                self.update_asset(asset, ve_allocated)
            except elasticsearch.exceptions.NotFoundError:
                continue
