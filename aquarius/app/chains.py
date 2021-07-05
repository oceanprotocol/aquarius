#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging

from flask import Blueprint, Response
from aquarius.log import setup_logging
from aquarius.myapp import app
from oceandb_driver_interface import OceanDb

setup_logging()
chains = Blueprint("chains", __name__)
logger = logging.getLogger("aquarius")
es_instance = OceanDb(app.config["CONFIG_FILE"]).plugin
###########################
# Get Chain List
###########################


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
        chains = es_instance.driver.es.get(
            index=f"{es_instance.driver.db_index}_plus", id="chains", doc_type="_doc"
        )["_source"]
        return Response(json.dumps(chains), 200, content_type="application/json")
    except Exception as e:
        logger.error(f"Cannot get chains list: {str(e)}")
        return Response("No chains found", 404)


###########################
# Get Index status for a specific chainId
###########################


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
        last_block_record = es_instance.driver.es.get(
            index=f"{es_instance.driver.db_index}_plus",
            id="events_last_block_" + str(chain_id),
            doc_type="_doc",
        )["_source"]
        return Response(
            json.dumps(last_block_record), 200, content_type="application/json"
        )
    except Exception as e:
        logger.error(f"Cannot get index status for chain {chain_id}: {str(e)}")
        return Response(f"{chain_id} is not indexed", 404)
