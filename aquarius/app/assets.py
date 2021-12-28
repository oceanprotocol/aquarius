#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from hashlib import sha256

import elasticsearch
from eth_account.account import Account
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend
from flask import Blueprint, jsonify, request
from web3.main import Web3

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import sanitize_record
from aquarius.ddo_checker.shacl_checker import validate_dict
from aquarius.log import setup_logging
from aquarius.myapp import app


keys = KeyAPI(NativeECCBackend)
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
              "dataToken": "0x00018b5b84eA05930f9D0dB8FFbb3B93EF86983b",
              "created": "2021-04-02T18:00:01Z",
              "proof": {
                  "created": "2021-04-02T17:59:33Z",
                  "creator": "0x8aa92201E19E4930d4D25c0f7a245c1dCdD5A242",
                  "type": "AddressHash",
                  "signatureValue": "0xd23d2f28fcf152347e5b5f1064422ba0288dd608f0ea6cf433a3717fb735a92d"
              },
              "dataTokenInfo": {
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
        return sanitize_record(asset_record), 200
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
        return sanitize_record(asset_record["metadata"])
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

    return json.dumps(names), 200


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
        return es_instance.es.search(data)
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
                [
                    {
                        "message": "Invalid request content type: should be application/octet-stream"
                    }
                ]
            ),
            400,
        )

    pk = os.environ.get("PRIVATE_KEY", None)
    values = {"hash": "", "publicKey": "", "r": "", "s": "", "v": ""}
    if pk:
        raw = request.get_data()
        wallet = Account.from_key(private_key=pk)
        values["publicKey"] = wallet.address
        keys_pk = keys.PrivateKey(wallet.key)
        values["hash"] = sha256(raw).digest()
        signed = keys.ecdsa_sign(message_hash=values["hash"], private_key=keys_pk)
        values["v"] = (signed.v + 27) if signed.v <= 1 else signed.v
        values["r"] = (Web3.toHex(Web3.toBytes(signed.r).rjust(32, b"\0")),)
        values["s"] = (Web3.toHex(Web3.toBytes(signed.s).rjust(32, b"\0")),)
    try:
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return (
                jsonify(
                    error="Invalid payload. The request could not be converted into a dict."
                ),
                400,
            )

        version = data.get("version", None)
        if not version:
            return (jsonify([{"message": "no version provided for DDO."}]), 400)

        valid, errors = validate_dict(data)

        if valid:
            return jsonify(values)

        return (jsonify(errors=errors), 400)
    except json.decoder.JSONDecodeError as e:
        logger.error(f"json validate error: {str(e)}.")
        return jsonify(error=f"Encountered error when validating asset: {str(e)}."), 400
    except Exception as e:
        logger.error(f"validate_remote failed: {str(e)}.")
        return jsonify(error=f"Encountered error when validating asset: {str(e)}."), 500
