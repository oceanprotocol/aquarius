#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import elasticsearch
from flask import Blueprint, jsonify, request
import json
import logging
import os

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import (
    sanitize_record,
    sanitize_query_result,
    get_signature_vrs,
    get_allowed_publishers,
)
from aquarius.ddo_checker.shacl_checker import validate_dict
from aquarius.events.processors import (
    MetadataCreatedProcessor,
    MetadataUpdatedProcessor,
)
from aquarius.events.util import setup_web3, make_did
from aquarius.log import setup_logging
from aquarius.myapp import app
from aquarius.events.purgatory import Purgatory
from aquarius.rbac import RBAC
from artifacts import ERC721Template
from web3.logs import DISCARD


setup_logging()
assets = Blueprint("assets", __name__)

logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance(app.config["AQUARIUS_CONFIG_FILE"])


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
        return jsonify(sanitize_query_result(es_instance.es.search(data)))
    except elasticsearch.exceptions.TransportError as e:
        error = e.error if isinstance(e.error, str) else str(e.error)
        info = e.info if isinstance(e.info, dict) else ""
        logger.info(
            f"Received elasticsearch TransportError: {error}, more info: {info}."
        )
        return (jsonify(error=error, info=info), e.status_code)
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
      - name: transactionId
        required: true
        description: transaction id containing MetadataCreated or MetadataUpdated event
      - name: logIndex
        required: false
        description: zero-based index in log if transaction contains more events
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
        log_index = int(data.get("logIndex", 0))

        config_file = app.config["AQUARIUS_CONFIG_FILE"]
        web3 = setup_web3(config_file)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_id)

        if len(tx_receipt.logs) <= log_index or log_index < 0:
            return jsonify(error=f"Log index {log_index} not found"), 400

        dt_address = tx_receipt.logs[log_index].address
        dt_contract = web3.eth.contract(
            abi=ERC721Template.abi, address=web3.toChecksumAddress(dt_address)
        )
        created_event = dt_contract.events.MetadataCreated().processReceipt(
            tx_receipt, errors=DISCARD
        )
        updated_event = dt_contract.events.MetadataUpdated().processReceipt(
            tx_receipt, errors=DISCARD
        )

        if not created_event and not updated_event:
            return jsonify(error="No metadata created/updated event found in tx."), 400

        es_instance = ElasticsearchInstance(config_file)
        allowed_publishers = get_allowed_publishers()
        purgatory = (
            Purgatory(es_instance)
            if (os.getenv("ASSET_PURGATORY_URL") or os.getenv("ACCOUNT_PURGATORY_URL"))
            else None
        )
        chain_id = web3.eth.chain_id
        processor_args = [es_instance, web3, allowed_publishers, purgatory, chain_id]

        processor = (
            MetadataCreatedProcessor if created_event else MetadataUpdatedProcessor
        )
        event_to_process = created_event[0] if created_event else updated_event[0]
        event_processor = processor(
            *([event_to_process, dt_contract, tx_receipt["from"]] + processor_args)
        )
        event_processor.process()
        did = make_did(dt_address, chain_id)

        response = app.response_class(
            response=sanitize_record(es_instance.get(did)),
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
