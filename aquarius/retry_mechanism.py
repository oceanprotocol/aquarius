#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from datetime import datetime, timedelta, timezone
import elasticsearch
from hashlib import sha256
from hexbytes import HexBytes
import logging
import json
import os

from web3.datastructures import AttributeDict
from web3.main import Web3

from aquarius.events.util import setup_web3, make_did


logger = logging.getLogger(__name__)

# All queue elements are stored in index self._retries_db_index
#
#
# Each element looks like:
#    {
#       "type":   "block" | "event" | "tx"
#       "create_timestamp": timestamp of first seen
#       "chainId":  chainId for this element
#       "number_retries": how many times we retryed this element
#       "next_retry": timestamp of next retry
#       "data":  { block } for block,  { txId, log_index (optional)} for tx,  { "txt":  Web3.to_json(event) } for events
#       "id":  sha256(data)
#       "nft_address":  only for events
#       "did":  only for events
#
# }
#
# Note:   since web3 tx logs cannot be stored as json, we need to unpack them (Web3.to_json) and then pack them (HexBytes, AttributeDict)


class RetryMechanism:
    def __init__(
        self,
        es_instance,
        retries_db_index,
        purgatory,
        chain_id,
        event_monitor_instance,
    ):
        self._es_instance = es_instance
        self._retries_db_index = retries_db_index
        self._purgatory = purgatory
        self._chain_id = chain_id
        self._web3 = setup_web3()
        self.retry_interval = timedelta(minutes=5)
        self._event_monitor_instance = event_monitor_instance
        try:
            # defaults to two weeks
            self.max_hold = int(os.getenv("PROCESS_RETRY_MAX_HOLD", 1209600))
        except ValueError:
            self.max_hold = 1209600

    def clear_all(self):
        q = {"match_all": {}}

        self._es_instance.es.delete_by_query(
            index=self._retries_db_index, body={"query": q}
        )

    def get_by_id(self, rm_id):
        try:
            return self._es_instance.es.get(index=self._retries_db_index, id=rm_id)[
                "_source"
            ]
        except Exception:
            return None

    def get_all(self):
        # logger.debug(f"Fetching all queue elements from index {self._retries_db_index}")
        q = {"match_all": {}}
        result = self._es_instance.es.search(index=self._retries_db_index, query=q)

        return result["hits"]["hits"]

    def get_from_retry_queue(self):
        q = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "next_retry": {
                                "lt": int(datetime.now(timezone.utc).timestamp())
                            }
                        }
                    },
                    {"term": {"chain_id": self._chain_id}},
                ]
            }
        }

        result = self._es_instance.es.search(index=self._retries_db_index, query=q)

        return result["hits"]["hits"]

    def delete_by_id(self, element_id):
        # logger.debug(f"Removing {element_id} from index {self._retries_db_index}")
        try:
            res = self._es_instance.es.delete(
                index=self._retries_db_index,
                id=element_id,
                refresh="wait_for",
            )
            logger.error(res)
        except Exception:
            logger.error(f"Failed to remove retry element {element_id} from es")
            pass

    def create_id(self, element):
        """Creates queue element id

        Args:
            element
        """
        params = {
            "chain_id": element["chain_id"],
            "type": element["type"],
            "data": element["data"],
        }
        id = sha256(json.dumps(params).encode("utf-8")).hexdigest()

        return id

    def add_block_to_retry_queue(self, block_number):
        """Add block to retry queue

        Args:
            block_number
        """
        element = {
            "type": "block",
            "chain_id": self._chain_id,
            "number_retries": 0,
            "next_retry": 0,
            "data": {"block": str(block_number)},
            "create_timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        id = self.create_id(element)
        element["id"] = id
        self.add_element_to_retry_queue(element)
        return id

    def add_tx_to_retry_queue(self, tx_id, log_index=None):
        """Add transaction to retry queue

        Args:
            tx_id
        """
        element = {
            "type": "tx",
            "chain_id": self._chain_id,
            "number_retries": 0,
            "next_retry": 0,
            "data": {"txId": str(tx_id)},
            "create_timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        if log_index:
            element["data"]["log_index"] = log_index
        id = self.create_id(element)
        element["id"] = id
        self.add_element_to_retry_queue(element)
        return id

    def add_event_to_retry_queue(self, event, nft_address: None, error: None):
        """Add event to retry queue

        Args:
            event
        """

        did = make_did(nft_address, self._chain_id) if nft_address else None
        element = {
            "type": "event",
            "nft_address": nft_address,
            "did": did,
            "chain_id": self._chain_id,
            "number_retries": 0,
            "next_retry": 0,
            "data": {"txt": Web3.to_json(event)},
            "error": error,
            "create_timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        id = self.create_id(element)
        element["id"] = id
        self.add_element_to_retry_queue(element)
        return id

    def add_element_to_retry_queue(self, element):
        """Adds element to retry queue. If element exists, updates number_retries & next_retry

        Args:
            element
        """
        id = element.get("id", None)
        if not id:
            return
        try:
            result = self.get_by_id(id)
            element["number_retries"] = result["number_retries"] + 1
        except Exception:
            element["number_retries"] = 0
            pass

        element["next_retry"] = int(
            (
                datetime.now(timezone.utc)
                + (element["number_retries"] + 1) * self.retry_interval
            ).timestamp()
        )
        try:
            self._es_instance.es.index(
                index=self._retries_db_index,
                id=id,
                body=element,
                refresh="wait_for",
            )["_id"]
            logger.info(f"Added {id} to retry queue")
        except elasticsearch.exceptions.RequestError:
            logger.error(f"Cannot add {element} to retry queue: ES RequestError")

    def process_queue(self):
        # possible improvements: order by closest, take only a fixed number from the queue
        # delete from retry queue after a certain number of retries
        queue_elements = self.get_from_retry_queue()
        for queue_element in queue_elements:
            element_id = queue_element["_id"]
            queue_element = queue_element["_source"]
            old_number_retries = queue_element["number_retries"]
            created_timestamp = queue_element["create_timestamp"]
            now = int(datetime.now().timestamp())
            if now > (created_timestamp + self.max_hold):
                logger.debug(
                    f"{now} > {(created_timestamp + self.max_hold)} -> deleting event {element_id} from retry_queue"
                )
                # we are keeping this for too long, delete it
                self.delete_by_id(element_id)
                continue
            self.handle_retry(queue_element)
            # read it again, to see if element was updated
            new_element = self.get_by_id(element_id)
            if new_element["number_retries"] == old_number_retries:
                # element was not updated, it means it was processed without error
                self.delete_by_id(element_id)
            else:
                # element was updated, it has new number_retries & next_retry
                logger.debug(f"Still unsuccessful. Will retry {element_id} again.")

    def handle_retry(self, element):
        """Tries to process an element, based on type

        Args:
            element
        """
        if element["type"] == "tx":
            self.handle_tx_retry(
                element["data"]["txId"], element["data"].get("log_index", None)
            )
        elif element["type"] == "event":
            obj = json.loads(element["data"]["txt"])
            # we need to convert back to proper event object (AttributeDIct, hexBytes)
            obj["transactionHash"] = HexBytes(obj["transactionHash"])
            obj["blockHash"] = HexBytes(obj["blockHash"])
            for idx, x in enumerate(obj["topics"]):
                obj["topics"][idx] = HexBytes(obj["topics"][idx])
            obj = AttributeDict(obj)
            self._event_monitor_instance.process_logs([obj], None)
        elif element["type"] == "block":
            self._event_monitor_instance.get_and_process_logs(
                from_block=int(element["data"]["block"]),
                to_block=int(element["data"]["block"]),
            )

    def handle_tx_retry(self, tx_id, log_index):
        try:
            # we don't need to wait more than 1 sec. if tx is not there, we will retry later
            tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_id, timeout=1)
        except Exception:
            # put it back to queue
            self.add_tx_to_retry_queue(tx_id, log_index)
            return
        for log in tx_receipt.logs:
            if (log_index and log["logIndex"] == log_index) or (not log_index):
                self._event_monitor_instance.process_logs([log], None)
        # there is no error checks, because if one event fails, it will be stored as event in queue, and not as tx anymore
