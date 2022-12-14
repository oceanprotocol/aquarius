#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging

import elasticsearch
from flask import Blueprint, jsonify, request

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
state = Blueprint("state", __name__)
logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance()


def get_retry_queue(chain_id, nft_address, did, retry_type):
    if chain_id is None and nft_address is None and did is None and retry_type is None:
        q = {"match_all": {}}
    else:
        conditions = []
        if chain_id:
            conditions.append({"term": {"chain_id": chain_id}})
        if nft_address:
            conditions.append({"match": {"nft_address": nft_address}})
        if did:
            conditions.append({"term": {"did": did}})
        if retry_type:
            conditions.append({"term": {"type": retry_type}})
        q = {"bool": {"filter": conditions}}
        return es_instance.es.search(
            index=f"{es_instance.db_index}_retries", query=q, from_=0, size=10000
        )


@state.route("/retryQueue", methods=["GET"])
def route_get_retry_queue():
    """Returns the current retry queue for all chains
    ---
    responses:
      200:
        description: successful operation.
    """
    data = request.args
    try:
        result = get_retry_queue(
            data.get("chainId"), data.get("nft"), data.get("did"), data.get("type")
        )
        return jsonify(result.body)
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )


def get_did_state(chain_id, nft_address, tx_id, did):
    if chain_id is None and nft_address is None and did is None and tx_id is None:
        q = {"match_all": {}}
    else:
        conditions = []
        if chain_id:
            conditions.append({"term": {"chain_id": chain_id}})
        if nft_address:
            conditions.append({"match": {"nft": nft_address}})
        if tx_id:
            conditions.append({"match": {"tx_id": tx_id}})
        if did:
            conditions.append({"term": {"_id": did}})
        q = {"bool": {"filter": conditions}}
    return es_instance.es.search(index=es_instance._did_states_index, query=q)


@state.route("/ddo", methods=["GET"])
def route_get_did_state():
    """Returns the current state for a did
    ---
    responses:
      200:
        description: successful operation.
    """
    data = request.args
    if not data.get("nft") and not data.get("txId") and not data.get("did"):
        return (
            jsonify(error="You need to specify one of: nft, txId, did"),
            400,
        )
    try:
        result = get_did_state(
            data.get("chainId"), data.get("nft"), data.get("txId"), data.get("did")
        )
        return jsonify(result.body["hits"]["hits"][0]["_source"])
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )
