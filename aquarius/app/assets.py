#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import elasticsearch
import json
import logging

from flask import Blueprint, jsonify, request, Response
from aquarius.ddo_checker.ddo_checker import (
    is_valid_dict_local,
    list_errors_dict_local,
    is_valid_dict_remote,
    list_errors_dict_remote,
)

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import (
    datetime_converter,
    get_metadata_from_services,
    sanitize_record,
    list_errors,
    get_request_data,
    encrypt_data,
)
from aquarius.log import setup_logging
from aquarius.myapp import app
from web3 import Web3

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
                          "curation": {
                              "rating": 0.0,
                              "numVotes": 0,
                              "isListed": true
                          },
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
              "accessWhiteList": [],
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
        return Response(
            sanitize_record(asset_record), 200, content_type="application/json"
        )
    except elasticsearch.exceptions.NotFoundError:
        return f"{did} asset DID is not in ES", 404
    except Exception as e:
        logger.error(f"get_ddo: {str(e)}")
        return f"{did} asset DID is not in ES", 404


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
            "curation": {
                "rating": 0.0,
                "numVotes": 0,
                "isListed": true
            },
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
        metadata = get_metadata_from_services(asset_record["service"])
        return Response(sanitize_record(metadata), 200, content_type="application/json")
    except Exception as e:
        logger.error(f"get_metadata: {str(e)}")
        return f"{did} asset DID is not in ES", 404


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
    try:
        data = get_request_data(request)
        assert isinstance(
            data, dict
        ), "invalid `args` type, should already be formatted into a dict."
        if "didList" not in data:
            return jsonify(error="`didList` is required in the request payload."), 400

        did_list = data.get("didList", [])
        if not did_list:
            return jsonify(message="the requested didList is empty"), 400

        names = dict()
        for did in did_list:
            try:
                asset_record = es_instance.get(did)
                metadata = get_metadata_from_services(asset_record["service"])
                names[did] = metadata["main"]["name"]
            except Exception:
                names[did] = ""

        return Response(json.dumps(names), 200, content_type="application/json")
    except Exception as e:
        logger.error(f"get_assets_names failed: {str(e)}")
        return jsonify(error=f" get_assets_names failed: {str(e)}"), 404


@assets.route("/ddo/query", methods=["POST"])
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
    """
    assert isinstance(request.json, dict), "invalid payload format."

    data = request.json

    try:
        return es_instance.es.search(data)
    except elasticsearch.exceptions.TransportError as e:
        logger.error(f"Received elasticsearch TransportError: {str(e)}")
        return jsonify(error="Received elasticsearch TransportError. Please refine the search."), 507


@assets.route("/ddo/validate", methods=["POST"])
def validate():
    """Validate metadata content.
    ---
    tags:
      - ddo
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Asset metadata.
        schema:
          type: object
    responses:
      200:
        description: successfully request.
        example:
          application/json: true
      500:
        description: Error
    """
    assert isinstance(request.json, dict), "invalid payload format."
    data = request.json
    assert isinstance(data, dict), "invalid `body` type, should be formatted as a dict."

    if is_valid_dict_local(data):
        return jsonify(True)
    else:
        res = jsonify(list_errors(list_errors_dict_local, data))
        return res


@assets.route("/ddo/validate-remote", methods=["POST"])
def validate_remote():
    """Validate DDO content.
    ---
    tags:
      - ddo
    consumes:
      - application/json
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
        example:
          application/json: true
      400:
        description: Invalid DDO format
      500:
        description: Error
    """
    assert isinstance(request.json, dict), "invalid payload format."
    data = request.json
    assert isinstance(data, dict), "invalid `body` type, should be formatted as a dict."

    if "service" not in data:
        return jsonify(message="Invalid DDO format."), 400

    data = get_metadata_from_services(data["service"])

    if "main" not in data:
        return jsonify(message="Invalid DDO format."), 400

    if is_valid_dict_remote(data):
        return jsonify(True)
    else:
        res = jsonify(list_errors(list_errors_dict_remote, data))
        return res


###########################
# ENCRYPT DDO
# Since this methods are public, this is just an example of how to do. You should either add some auth methods here, or protect this endpoint from your nginx
# Using it like this, means that anyone call encrypt their ddo, so they will be able to publish to your market.
###########################
@assets.route("/ddo/encrypt", methods=["POST"])
def encrypt_ddo():
    """Encrypt a DDO.
    ---
    tags:
      - ddo
    consumes:
      - application/octet-stream
    parameters:
      - in: body
        name: body
        required: true
        description: data
        schema:
          type: object
    responses:
      200:
        description: successfully request.
      400:
        description: Invalid format
      500:
        description: Error
    """
    if request.content_type != "application/octet-stream":
        return "invalid content-type", 400
    data = request.get_data()
    result, encrypted_data = encrypt_data(data)
    if not result:
        return encrypted_data, 400

    response = Response(encrypted_data)
    response.headers.set("Content-Type", "application/octet-stream")
    return response


@assets.route("/ddo/encryptashex", methods=["POST"])
def encrypt_ddo_as_hex():
    """Encrypt a DDO.
    ---
    tags:
      - ddo
    consumes:
      - application/octet-stream
    parameters:
      - in: body
        name: body
        required: true
        description: data
        schema:
          type: object
    responses:
      200:
        description: successfully request. data is converted to hex
        example:
          text/plain:
            "0x041a1953f19ca7410bcbef240a65246399d477765b966aef3553b3c89cc5837943706359e44f3b991"
      400:
        description: Invalid format
      500:
        description: Error
    """
    data = request.get_data()
    result, encrypted_data = encrypt_data(data)
    if not result:
        return encrypted_data, 400

    response = Response(Web3.toHex(encrypted_data))
    response.headers.set("Content-Type", "text/plain")
    return response
