from datetime import datetime, timedelta
import elasticsearch
from hashlib import sha256
import json
import logging
from web3.logs import DISCARD

from aquarius.app.util import get_allowed_publishers, sanitize_record
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.util import setup_web3, make_did

from jsonsempai import magic  # noqa: F401
from artifacts import ERC721Template

logger = logging.getLogger(__name__)


class RetryMechanism:
    def __init__(self, config_file, es_instance, retries_db_index, purgatory):
        self._es_instance = es_instance
        self._retries_db_index = retries_db_index
        self._purgatory = purgatory
        self._web3 = setup_web3(config_file)
        self.retry_interval = timedelta(minutes=5)

    def clear_all(self):
        q = {"match_all": {}}

        self._es_instance.es.delete_by_query(
            index=self._retries_db_index, body={"query": q}
        )

    def get_by_id(self, rm_id):
        return self._es_instance.es.get(
            index=self._retries_db_index, id=rm_id, doc_type="queue"
        )["_source"]

    def add_to_retry_queue(self, tx_id, log_index, chain_id, asap=False):
        params = {"tx_id": tx_id, "log_index": log_index, "chain_id": chain_id}

        rm_id = sha256(json.dumps(params).encode("utf-8")).hexdigest()

        try:
            result = self.get_by_id(rm_id)
            params["number_retries"] = result["number_retries"] + 1
        except Exception:
            params["number_retries"] = 0
            pass

        params["next_retry"] = int(
            (
                datetime.utcnow() + (params["number_retries"] + 1) * self.retry_interval
            ).timestamp()
        )

        if asap:
            params["number_retries"] = 0
            params["next_retry"] = int(datetime.utcnow().timestamp())

        try:
            self._es_instance.es.index(
                index=self._retries_db_index,
                id=rm_id,
                body=params,
                doc_type="queue",
                refresh="wait_for",
            )["_id"]
            logger.info(f"Added {rm_id} to retry queue")
        except elasticsearch.exceptions.RequestError:
            logger.error(f"Cannot add {rm_id} to retry queue: ES RequestError")

    def get_all(self):
        q = {"match_all": {}}
        result = self._es_instance.es.search(index=self._retries_db_index, query=q)

        return result["hits"]["hits"]

    def get_from_retry_queue(self):
        q = {"range": {"next_retry": {"lt": int(datetime.utcnow().timestamp())}}}

        result = self._es_instance.es.search(index=self._retries_db_index, query=q)

        return result["hits"]["hits"]

    def delete_by_id(self, element_id):
        try:
            self._es_instance.es.delete(
                index=self._retries_db_index,
                id=element_id,
                doc_type="queue",
            )
        except Exception:
            pass

    def process_queue(self):
        # possible improvements: order by closest, take only a fixed number from the queue
        # delete from retry queue after a certain number of retries
        queue_elements = self.get_from_retry_queue()
        for queue_element in queue_elements:
            element_id = queue_element["_id"]
            queue_element = queue_element["_source"]
            success, message = self.handle_retry(
                queue_element["tx_id"],
                queue_element["log_index"],
                queue_element["chain_id"],
            )

            if success:
                self.delete_by_id(element_id)
            else:
                logger.debug(f"Still unsuccessful. Will retry {element_id} again.")
                self.add_to_retry_queue(
                    queue_element["tx_id"],
                    queue_element["log_index"],
                    queue_element["chain_id"],
                )

    def handle_retry(self, tx_id, log_index, chain_id):
        try:
            # we don't need to wait more than 1 sec. if tx is not there, we will retry later
            tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_id, timeout=1)
        except Exception:
            return False, "Failed to get receipt, will try next time"

        if len(tx_receipt.logs) <= log_index or log_index < 0:
            return False, f"Log index {log_index} not found"

        dt_address = tx_receipt.logs[log_index].address
        dt_contract = self._web3.eth.contract(
            abi=ERC721Template.abi, address=dt_address
        )
        created_event = dt_contract.events.MetadataCreated().processReceipt(
            tx_receipt, errors=DISCARD
        )
        updated_event = dt_contract.events.MetadataUpdated().processReceipt(
            tx_receipt, errors=DISCARD
        )

        if not created_event and not updated_event:
            return False, "No metadata created/updated event found in tx."

        allowed_publishers = get_allowed_publishers()
        processor_args = [
            self._es_instance,
            self._web3,
            allowed_publishers,
            self._purgatory,
            chain_id,
        ]

        try:
            processor = (
                MetadataCreatedProcessor if created_event else MetadataUpdatedProcessor
            )
            event_to_process = created_event[0] if created_event else updated_event[0]
            event_processor = processor(
                *([event_to_process, dt_contract, tx_receipt["from"]] + processor_args)
            )
            event_processor.process()
            did = make_did(dt_address, chain_id)

            return True, sanitize_record(self._es_instance.get(did))
        except Exception:
            return False, "new exception in processor, retry again"
