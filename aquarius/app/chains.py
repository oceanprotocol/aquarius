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
chains = Blueprint("chains", __name__)
logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance()


@chains.route("/list", methods=["GET"])
def get_chains_list():
    """Get chains list
    ---
    tags:
      - chains
    responses:
      200:
        description: successful operation.
      404:
        description: No chains are present
    """
    try:
        chains = es_instance.es.get(index=f"{es_instance.db_index}_plus", id="chains")[
            "_source"
        ]
        return jsonify(chains)
    except (elasticsearch.exceptions.NotFoundError, KeyError):
        logger.error("Cannot get chains list.")
        return jsonify(error="No chains found."), 404
    except Exception as e:
        logger.error(f"Error in get_chains_list: {str(e)}")
        return jsonify(error=f"Error retrieving chains: {str(e)}."), 404


@chains.route("/status/<chain_id>", methods=["GET"])
def get_index_status(chain_id):
    """Get index status for a specific chain_id
    ---
    tags:
      - chains
    parameters:
      - name: chain_id
        in: path
        description: chainId
        required: true
        type: number
    responses:
      200:
        description: successful operation.
      404:
        description: This chainId is not indexed.
    """
    try:
        last_block_record = es_instance.es.get(
            index=f"{es_instance.db_index}_plus",
            id="events_last_block_" + str(chain_id),
        )["_source"]
        return jsonify(last_block_record)
    except (elasticsearch.exceptions.NotFoundError, KeyError):
        logger.error(f"Cannot get index status for chain {chain_id}. Chain not found.")
        return jsonify(error=f"Chain {chain_id} is not indexed."), 404
    except Exception as e:
        logger.error(
            f"Cannot get index status for chain {chain_id}. Error encountered is: {str(e)}"
        )
        return jsonify(error=f"Error retrieving chain {chain_id}: {str(e)}."), 404


@chains.route("/retryQueue", methods=["GET"])
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
            conditions.append({"term": {"nft_address": nft_address}})
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
