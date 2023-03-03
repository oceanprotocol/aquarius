#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging

import elasticsearch
from flask import Blueprint, jsonify, request

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import get_did_state, get_retry_queue
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
state = Blueprint("state", __name__)
logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance()


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
            es_instance,
            data.get("chainId"),
            data.get("nft"),
            data.get("did"),
            data.get("type"),
        )
        return jsonify(result.body)
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )


@state.route("/ddo", methods=["GET"])
def route_get_did_state():
    """Returns the current state for a did
    ---
    parameters:
      - name: did
        in: path
        description: DID of the asset.
        required: false
        type: string
      - name: txId
        in: path
        description: transaction id
        required: false
        type: string
      - name: nft
        in: path
        description: nft address
        required: false
        type: string
    responses:
      200:
        description: successful operation.
      400:
        description: missing all inputs.
    """
    data = request.args
    if not data.get("nft") and not data.get("txId") and not data.get("did"):
        return (
            jsonify(error="You need to specify one of: nft, txId, did"),
            400,
        )
    try:
        result = get_did_state(
            es_instance,
            data.get("chainId"),
            data.get("nft"),
            data.get("txId"),
            data.get("did"),
        )
        return jsonify(result.body["hits"]["hits"][0]["_source"])
    except Exception as e:
        return (
            jsonify(error=f"Encountered error : {str(e)}."),
            500,
        )
