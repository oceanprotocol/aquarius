from datetime import datetime, timedelta
import elasticsearch
from hashlib import sha256
import json
import logging
from web3.logs import DISCARD

from aquarius.app.util import get_allowed_publishers
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.util import setup_web3

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

    def add_to_retry_queue(self, tx_id, log_index, chain_id, asap=False):
        params = {
            "tx_id": tx_id,
            "log_index": log_index,
            "chain_id": chain_id
        }

        rm_id = sha256(json.dumps(params).encode("utf-8")).hexdigest()
        try:
            self._es_instance.es.get(
                index=self._retries_db_index, id=rm_id, doc_type="_doc"
            )["_source"]

            # TODO: update the timestamp; if asap, then now
        except Exception:
            pass

        params["number_retries"] = 0
        params["next_retry"] = (datetime.utcnow() + self.retry_interval).timestamp()

        try:
            self._es_instance.es.index(
                index=self._retries_db_index,
                id=rm_id,
                body=params,
                doc_type="_doc",
                refresh="wait_for",
            )["_id"]
            logger.info(f"Added todo to retry queue")
        except elasticsearch.exceptions.RequestError:
            logger.error(
                f"Cannot add todo to retry queue: ES RequestError"
            )

    def get_from_retry_queue(self):
        q = {
            "range": {
                "next_retry": {"lte": datetime.utcnow().timestamp()}
            }
        }

        result = self._es_instance.es.search(
            index=self._retries_db_index,
            query=q
        )

        return result["hits"]["hits"]

    def handle_retry(self, tx_id, log_index, chain_id):
        tx_receipt = self._web3.eth.wait_for_transaction_receipt(tx_id)

        if len(tx_receipt.logs) <= log_index or log_index < 0:
            return False, f"Log index {log_index} not found"

        dt_address = tx_receipt.logs[log_index].address
        dt_contract = self._web3.eth.contract(abi=ERC721Template.abi, address=dt_address)
        created_event = dt_contract.events.MetadataCreated().processReceipt(
            tx_receipt, errors=DISCARD
        )
        updated_event = dt_contract.events.MetadataUpdated().processReceipt(
            tx_receipt, errors=DISCARD
        )

        if not created_event and not updated_event:
            return False, "No metadata created/updated event"

        allowed_publishers = get_allowed_publishers()
        processor_args = [self._es_instance, self._web3, allowed_publishers, self._purgatory, chain_id]

        processor = (
            MetadataCreatedProcessor if created_event else MetadataUpdatedProcessor
        )
        event_to_process = created_event[0] if created_event else updated_event[0]
        event_processor = processor(
            *([event_to_process, dt_contract, tx_receipt["from"]] + processor_args)
        )
        return event_processor.process()

