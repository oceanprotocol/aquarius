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

from aquarius.app.dao import Dao
from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import (
    make_paginate_response,
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

dao = Dao(config_file=app.config["CONFIG_FILE"])
logger = logging.getLogger("aquarius")
es_instance = ElasticsearchInstance(app.config["CONFIG_FILE"])


@assets.route("", methods=["GET"])
def get_assets_ids():
    """Get all asset IDs.
    ---
    tags:
      - ddo
    responses:
      200:
        description: successful action
    """
    asset_with_id = dao.get_all_listed_assets()
    asset_ids = [a["id"] for a in asset_with_id if "id" in a]
    return Response(json.dumps(asset_ids), 200, content_type="application/json")


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
        description: successful operation
      404:
        description: This asset DID is not in ES.
    """
    try:
        asset_record = dao.get(did)
        return Response(
            sanitize_record(asset_record), 200, content_type="application/json"
        )
    except elasticsearch.exceptions.NotFoundError:
        return f"{did} asset DID is not in ES", 404
    except Exception as e:
        logger.error(f"get_ddo: {str(e)}")
        return f"{did} asset DID is not in ES", 404


@assets.route("/ddo", methods=["GET"])
def get_asset_ddos():
    """Get DDO of all assets.
    ---
    tags:
      - ddo
    responses:
      200:
        description: successful action
    """
    _assets = dao.get_all_listed_assets()
    for _record in _assets:
        sanitize_record(_record)
    return Response(
        json.dumps(_assets, default=datetime_converter),
        200,
        content_type="application/json",
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
      404:
        description: This asset DID is not in ES.
    """
    try:
        asset_record = dao.get(did)
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
                asset_record = dao.get(did)
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
    """Get a list of DDOs that match with the executed query.
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
          properties:
            query:
              type: string
              description: Query to realize
              example: {"value":1}
            sort:
              type: object
              description: Key or list of keys to sort the result
              example: {"value":1}
            offset:
              type: int
              description: Number of records per page
              example: 100
            page:
              type: int
              description: Page showed
              example: 1
    responses:
      200:
        description: successful action

    example:
        {"query": {"query_string": {"query": "(covid) -isInPurgatory:true"}}, "offset":1, "page": 1}

    """
    assert isinstance(request.json, dict), "invalid payload format."
    data = request.json
    query = data.get("query")

    querystr = json.dumps(query)
    did_str = "did:op:"
    esc_did_str = "did\\\:op\\\:"  # noqa
    querystr = querystr.replace(esc_did_str, did_str)
    data["query"] = json.loads(querystr.replace(did_str, esc_did_str))

    data.setdefault("page", 1)
    data.setdefault("offset", 100)

    query_result = dao.run_es_query(data)

    for ddo in query_result[0]:
        sanitize_record(ddo)

    response = make_paginate_response(
        query_result, data.get("offset"), data.get("page")
    )
    return Response(
        json.dumps(response, default=datetime_converter),
        200,
        content_type="application/json",
    )


@assets.route("/ddo/es-query", methods=["POST"])
def es_query():
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
    return es_instance.es.search(data)


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
        description: successfully request. data is converted to hex
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
