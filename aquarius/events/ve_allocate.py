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
from web3 import Web3

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
            return {
                (a["nft_addr"], a["ve_allocated"], a["chainID"])
                for a in response.json()
                if a and "nft_addr" in a and "ve_allocated" in a and "chainID" in a
            }

        logger.error(f"veAllocate: Failed to retrieve list from {env_var} env var.")
        return set()

    def update_asset(self, asset, veAllocated):
        """
        Updates the field `state.allocated`  in `asset` object.
        """
        did = asset["id"]
        if "stats" not in asset:
            asset["stats"] = {"allocated": 0}
        if "allocated" not in asset["stats"]:
            asset["stats"]["allocated"] = 0
        if asset["stats"]["allocated"] != veAllocated:
            asset["stats"]["allocated"] = veAllocated
            logger.info(
                f"veAllocate: updating asset {did} with state.allocated={veAllocated}."
            )
            try:
                self._es_instance.update(json.dumps(asset), did)
            except Exception as e:
                logger.warning(
                    f"updating ddo {did} stats.allocated attribute failed: {e}"
                )
        else:
            logger.debug(
                f"veAllocate: asset {did} has unchanged state.allocated ({veAllocated})."
            )

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
        logger.info(f"veAllocate: Retrieved list of {len(ve_list)} assets to update")

        for nft, ve_allocated, chain_id in ve_list:
            did = make_did(Web3.toChecksumAddress(nft), chain_id)
            try:
                asset = self._es_instance.read(did)
                self.update_asset(asset, ve_allocated)
            except elasticsearch.exceptions.NotFoundError:
                logger.debug(f"Cannot find asset {did} for veAllocate update")
                continue
