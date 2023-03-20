#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from datetime import datetime
from eth_utils.address import to_checksum_address

import elasticsearch
import requests
from web3 import Web3


from aquarius.events.util import get_defined_block, make_did
from aquarius.graphql import get_nft_transfers
from elasticsearch.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class NftOwnership:
    def __init__(self, es_instance, db_index, chain_id, events_monitor):
        self.update_time = None
        self._es_instance = es_instance
        self._db_index = db_index
        self._chain_id = chain_id
        self._index_name = "nft_events_" + str(self._chain_id)
        self._events_monitor = events_monitor

    def get_last_processed_block(self):
        """Get last processed_block, fallback to contract deployment block"""
        block = get_defined_block(self._chain_id)
        try:
            # Re-establishing the connection with ES
            while True:
                try:
                    if self._es_instance.es.ping() is True:
                        break
                except elasticsearch.exceptions.ElasticsearchException as es_err:
                    logging.error(f"Elasticsearch error: {es_err}")
                logging.error("Connection to ES failed. Trying to connect to back...")
                time.sleep(5)
            # logging.info("Stable connection to ES.")
            last_block_record = self._es_instance.es.get(
                index=self._db_index, id=self._index_name
            )["_source"]
            block = (
                last_block_record["last_block"]
                if last_block_record["last_block"] >= 0
                else get_defined_block(self._chain_id)
            )
        except Exception as e:
            # Retrieve the defined block.
            if type(e) == elasticsearch.NotFoundError:
                block = get_defined_block(self._chain_id)
                logger.info(f"Retrieved the default block. NotFound error occurred.")
            else:
                logging.error(f"Cannot get last_block error={e}")
        return block

    def store_last_processed_block(self, block):
        """Stores last processed block

        Args:
            block: last block that was processed
        """
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        logger.info(f"Storing last_processed_block {block}  (In Es: {stored_block})")
        if block <= stored_block:
            return
        record = {"last_block": block}
        try:
            self._es_instance.es.index(
                index=self._db_index,
                id=self._index_name,
                body=record,
                refresh="wait_for",
            )["_id"]

        except elasticsearch.exceptions.RequestError:
            logger.error(
                f"store_last_processed_block: block={block} type={type(block)}, ES RequestError"
            )

    def update_lists(self):
        """
        Grab and process all nft transfership events from subgraph, starting from last known block
        """
        start_block = self.get_last_processed_block()
        # never go past last indexed block, because we will not have the ddos
        end_block = self._events_monitor.get_last_processed_block()
        if end_block <= start_block:
            # no data to ingest
            return
        try:
            nft_transfers_list = get_nft_transfers(
                start_block, end_block, self._chain_id
            )
            if not nft_transfers_list:
                # nothing to process
                return
        except Exception as e:
            logger.warn(f"Failed to get subgraphs NFT transfer list: {e}")
            return
        for transfer in nft_transfers_list:
            did = make_did(transfer["nft"]["id"], self._chain_id)
            try:
                asset = self._es_instance.read(did)
                asset["nft"]["owner"] = to_checksum_address(transfer["newOwner"]["id"])
                self._es_instance.update(asset, did)
                logger.debug(f"Updated {did}: new owner: {asset['nft']['owner']}")
            except NotFoundError:
                logger.debug(
                    f"Unable to update new owner {transfer['newOwner']['id']} for did {did}:  Not Found"
                )
            except Exception as e:
                logger.error(
                    f"Unable to update new owner {transfer['newOwner']['id']} for did {did}:  {e}"
                )
            self.store_last_processed_block(transfer["block"])
