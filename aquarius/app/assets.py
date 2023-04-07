#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import elasticsearch
from flask import Blueprint, jsonify, request
from datetime import timedelta
import json
import logging
import os

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import (
    sanitize_record,
    sanitize_query_result,
    get_signature_vrs,
)
from aquarius.ddo_checker.shacl_checker import validate_dict
from aquarius.log import setup_logging
from aquarius.myapp import app
from aquarius.events.purgatory import Purgatory
from aquarius.retry_mechanism import RetryMechanism
from aquarius.rbac import RBAC


setup_logging()
assets = Blueprint("assets", __name__)

logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance()


@assets.route("/ddo/<did>", methods=["GET"])
def get_ddo(did):
    """Get DDO of a particular asset.
    ---
    tags:
      - ddo
    parameters:
      - name: did
        in: path
        description: DID of the asset.
        required: true
        type: string
    responses:
      200:
        description: On successful operation returns DDO information.
        example:
          application/json: {
              "@context": "https://w3id.org/did/v1",
              "id": "did:op:00018b5b84eA05930f9D0dB8FFbb3B93EF86983b",
              "publicKey": [
                  {
                      "id": "did:op:00018b5b84eA05930f9D0dB8FFbb3B93EF86983b",
                      "type": "EthereumECDSAKey",
                      "owner": "0x8aa92201E19E4930d4D25c0f7a245c1dCdD5A242"
                  }
              ],
              "authentication": [
                  {
                      "type": "RsaSignatureAuthentication2018",
                      "publicKey": "did:op:00018b5b84eA05930f9D0dB8FFbb3B93EF86983b"
                  }
              ],
              "service": [
                  {
                      "type": "metadata",
                      "attributes": {
                          "main": {
                              "type": "dataset",
                              "name": "Nu nl",
                              "dateCreated": "2021-04-02T17:59:32Z",
                              "author": "ab",
                              "license": "MIT",
                              "files": [
                                  {
                                      "index": 0,
                                      "contentType": "application/json"
                                  }
                              ],
                              "datePublished": "2021-04-20T22:56:01Z"
                          },
                          "encryptedFiles": "0x047c992274f3fa2bf9c5cc57d0e0852f7b3ec22d7ab4e798e3e73e77e7f97"
                      },
                      "index": 0
                  },
                  {
                      "type": "access",
                      "index": 1,
                      "serviceEndpoint": "https://provider.datatunnel.allianceblock.io",
                      "attributes": {
                          "main": {
                              "creator": "0x8aa92201E19E4930d4D25c0f7a245c1dCdD5A242",
                              "datePublished": "2021-04-02T17:57:57Z",
                              "cost": "1",
                              "timeout": 2592000000,
                              "name": "dataAssetAccess"
                          }
                      }
                  }
              ],
              "datatoken": "0x00018b5b84eA05930f9D0dB8FFbb3B93EF86983b",
              "created": "2021-04-02T18:00:01Z",
              "proof": {
                  "created": "2021-04-02T17:59:33Z",
                  "creator": "0x8aa92201E19E4930d4D25c0f7a245c1dCdD5A242",
                  "type": "AddressHash",
                  "signatureValue": "0xd23d2f28fcf152347e5b5f1064422ba0288dd608f0ea6cf433a3717fb735a92d"
              },
              "datatokenInfo": {
                  "address": "0x00018b5b84eA05930f9D0dB8FFbb3B93EF86983b",
                  "name": "Parsimonious Plankton Token",
                  "symbol": "PARPLA-59",
                  "decimals": 18,
                  "totalSupply": 100.0,
                  "cap": 1000.0,
                  "minter": "0x8aa92201E19E4930d4D25c0f7a245c1dCdD5A242",
                  "minterBalance": 99.999
              },
              "updated": "2021-04-02T18:00:01Z",
              "price": {
                  "datatoken": 0.0,
                  "ocean": 0.0,
                  "value": 0.0,
                  "type": "",
                  "exchange_id": "",
                  "address": "",
                  "pools": [],
                  "isConsumable": ""
              },
              "isInPurgatory": "false"
            }
        content:
          application/json:
            schema:
              type: object
      404:
        description: This asset DID is not in ES.
    """
    try:
        asset_record = es_instance.get(did)
        response = app.response_class(
            response=sanitize_record(asset_record),
            status=200,
            mimetype="application/json",
        )
        return response
    except elasticsearch.exceptions.NotFoundError:
        return jsonify(error=f"Asset DID {did} not found in Elasticsearch."), 404
    except Exception as e:
        return (
            jsonify(
                error=f"Error encountered while searching the asset DID {did}: {str(e)}."
            ),
            404,
        )


@assets.route("/metadata/<did>", methods=["GET"])
def get_metadata(did):
    """Get metadata of a particular asset
    ---
    tags:
      - metadata
    parameters:
      - name: did
        in: path
        description: DID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successful operation.
        example:
          application/json: {
            "main": {
                "type": "dataset",
                "name": "Nu nl",
                "dateCreated": "2021-04-02T17:59:32Z",
                "author": "ab",
                "license": "MIT",
                "files": [
                    {
                        "index": 0,
                        "contentType": "application/json"
                    }
                ],
                "datePublished": "2021-04-20T22:56:01Z"
            },
            "encryptedFiles": "0x047c992274f3fa2bf9c5cc57d0e0852f7b3ec22d7ab4e798e3e73e77e7f971ff04896129c9f58deac"
          }
      404:
        description: This asset DID is not in ES.
    """
    try:
        asset_record = es_instance.get(did)
        response = app.response_class(
            response=sanitize_record(asset_record["metadata"]),
            status=200,
            mimetype="application/json",
        )
        return response
    except Exception as e:
        logger.error(f"get_metadata: {str(e)}")
        return (
            jsonify(error=f"Error encountered while retrieving metadata: {str(e)}."),
            404,
        )


@assets.route("/names", methods=["POST"])
def get_assets_names():
    """Get names of assets as specified in the payload
    ---
    tags:
      - name
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: list of asset DIDs
        schema:
          type: object
          properties:
            didList:
              type: list
              description: list of dids
              example: ["did:op:123455644356", "did:op:533443322223344"]
    responses:
      200:
        description: successful operation.
        example:
          application/json: {
            "did:op:03115a5Dc5fC8Ff8DA0270E61F87EEB3ed2b3798": "SVM Classifier v2.0",
            "did:op:01738AA29Ce1D4028C0719F7A0fd497a1BFBe918": "Wine dataset 1.0"
          }
      404:
        description: assets not found
    """
    data = request.args if request.args else request.json
    if not isinstance(data, dict):
        return (
            jsonify(
                error="Invalid payload. The request could not be converted into a dict."
            ),
            400,
        )

    if "didList" not in data:
        return jsonify(error="`didList` is required in the request payload."), 400

    did_list = data.get("didList", [])
    if not did_list:
        return jsonify(error="The requested didList can not be empty."), 400
    if not isinstance(did_list, list):
        return jsonify(error="The didList must be a list."), 400

    names = dict()
    for did in did_list:
        try:
            asset_record = es_instance.get(did)
            names[did] = asset_record["metadata"]["name"]
        except Exception:
            names[did] = ""

    return jsonify(names)


@assets.route("/query", methods=["POST"])
def query_ddo():
    """Runs a native ES query.
    ---
    tags:
      - ddo
    consumes:
      - application/json
    responses:
      200:
        description: successful action
      500:
        description: elasticsearch exception
    """
    data = request.json
    if not isinstance(request.json, dict):
        return (
            jsonify(
                error="Invalid payload. The request could not be converted into a dict."
            ),
            400,
        )

    try:
        args = copy.deepcopy(data)
        if "from" in args.keys():
            args["from_"] = args.pop("from")
        result = es_instance.es.search(**args)
        return jsonify(sanitize_query_result(result.body))
    except elasticsearch.exceptions.TransportError as e:
        error = e.message
        logger.info(f"Received elasticsearch TransportError: {error}.")
        return (jsonify(error=error), 400)
    except Exception as e:
        logger.error(f"Received elasticsearch Error: {str(e)}.")
        return jsonify(error=f"Encountered Elasticsearch Exception: {str(e)}"), 500


@assets.route("/ddo/validate", methods=["POST"])
def validate_remote():
    """Validate DDO content.
    ---
    tags:
      - ddo
    consumes:
      - application/octet-stream
    parameters:
      - in: body
        name: body
        required: true
        description: Asset DDO.
        schema:
          type: object
    responses:
      200:
        description: successfully request.
      400:
        description: Invalid DDO format
      500:
        description: Error
    """
    if request.content_type != "application/octet-stream":
        return (
            jsonify(
                error="Invalid request content type: should be application/octet-stream"
            ),
            400,
        )

    raw = request.get_data()

    try:
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.decoder.JSONDecodeError:
            return (
                jsonify(
                    error="Invalid payload. The request could not be converted into a dict."
                ),
                400,
            )

        version = data.get("version", None)

        if os.getenv("RBAC_SERVER_URL"):
            valid = RBAC.validate_ddo_rbac(data)

            if not valid:
                return (
                    jsonify(error="DDO marked invalid by the RBAC server."),
                    400,
                )

        version = data.get("version", None)
        if not version:
            return (jsonify([{"message": "no version provided for DDO."}]), 400)

        valid, errors = validate_dict(
            data, data.get("chainId", ""), data.get("nftAddress", "")
        )

        if valid:
            return jsonify(get_signature_vrs(raw))

        return (jsonify(errors=errors), 400)
    except Exception as e:
        logger.error(f"validate_remote failed: {str(e)}.")
        return jsonify(error=f"Encountered error when validating asset: {str(e)}."), 500


@assets.route("/triggerCaching", methods=["POST"])
def trigger_caching():
    """Triggers manual caching of a specific transaction (MetadataCreated or MetadataUpdated event)
    ---
    tags:
      - name
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: JSON object containing transaction details
        schema:
          type: object
          properties:
            transactionId:
              type: string
              description: transaction id containing MetadataCreated or MetadataUpdated event
              example: "0xaabbccdd"
            chainId:
              type: int
              description: chain Id id of MetadataCreated or MetadataUpdated event
              example: 8996
            logIndex:
              type: int
              required: false
              description: log index for the event in the transaction
              example: 1
    responses:
      200:
        description: successful operation.
      400:
        description: bad request. Log index not found or event not found.
      500:
        description: server error/exception
    """
    try:
        data = request.args if request.args else request.json
        tx_id = data.get("transactionId")
        chain_id = data.get("chain_id")
        if not tx_id or not chain_id:
            return (
                jsonify(error="Invalid transactionId or chain_id"),
                400,
            )
        log_index = int(data.get("logIndex", 0))

        es_instance = ElasticsearchInstance()
        retries_db_index = f"{es_instance.db_index}_retries"
        purgatory = (
            Purgatory(es_instance)
            if (os.getenv("ASSET_PURGATORY_URL") or os.getenv("ACCOUNT_PURGATORY_URL"))
            else None
        )

        retry_mechanism = RetryMechanism(
            es_instance, retries_db_index, purgatory, chain_id, None
        )
        retry_mechanism.retry_interval = timedelta(seconds=1)
        retry_mechanism.add_tx_to_retry_queue(tx_id, log_index)
        response = app.response_class(
            response="Queued",
            status=200,
            mimetype="application/json",
        )
        return response
    except Exception as e:
        logger.error(f"trigger_caching failed: {str(e)}.")
        return (
            jsonify(error=f"Encountered error when triggering caching: {str(e)}."),
            500,
        )
