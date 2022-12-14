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


@state.route("/retryQueue", methods=["GET"])
def get_retry_queue():
    """Returns the current retry queue for all chains
    ---
    responses:
      200:
        description: successful operation.
    """
    data = request.args
    chain_id = data.get("chainId", None)
    nft_address = data.get("nft", None)
    did = data.get("did", None)
    retry_type = data.get("type", None)
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
    try:
        result = es_instance.es.search(index=f"{es_instance.db_index}_retries", query=q)
        return jsonify(result.body)
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )


@state.route("/ddo", methods=["GET"])
def get_did_state():
    """Returns the current state for a did
    ---
    responses:
      200:
        description: successful operation.
    """
    data = request.args
    chain_id = data.get("chainId", None)
    nft_address = data.get("nft", None)
    tx_id = data.get("txId", None)
    did = data.get("did", None)
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
    logger.debug(f"Execute query: {q}")
    try:
        result = es_instance.es.search(index=es_instance._did_states_index, query=q)
        return jsonify(result.body["hits"]["hits"])
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )
