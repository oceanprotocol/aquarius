#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import ecies
import elasticsearch
import json
import logging
import os

from flask import Blueprint, jsonify, request, Response
from oceandb_driver_interface.search_model import FullTextModel
from aquarius.ddo_checker.ddo_checker import (
    is_valid_dict_local,
    list_errors_dict_local,
    is_valid_dict_remote,
    list_errors_dict_remote,
)

from aquarius.app.dao import Dao
from aquarius.app.util import (
    make_paginate_response,
    datetime_converter,
    get_metadata_from_services,
    sanitize_record,
    list_errors,
    get_request_data,
)
from aquarius.log import setup_logging
from aquarius.myapp import app
from eth_account import Account
import eth_keys

setup_logging()
assets = Blueprint("assets", __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config["CONFIG_FILE"])
logger = logging.getLogger("aquarius")


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
        description: This asset DID is not in OceanDB
    """
    try:
        asset_record = dao.get(did)
        return Response(
            sanitize_record(asset_record), 200, content_type="application/json"
        )
    except elasticsearch.exceptions.NotFoundError:
        return f"{did} asset DID is not in OceanDB", 404
    except Exception as e:
        logger.error(f"get_ddo: {str(e)}")
        return f"{did} asset DID is not in OceanDB", 404


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
        description: This asset DID is not in OceanDB.
    """
    try:
        asset_record = dao.get(did)
        metadata = get_metadata_from_services(asset_record["service"])
        return Response(sanitize_record(metadata), 200, content_type="application/json")
    except Exception as e:
        logger.error(f"get_metadata: {str(e)}")
        return f"{did} asset DID is not in OceanDB", 404


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


###########################
# SEARCH
###########################
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
    metadata = dao.run_metadata_query(data)

    search_model = FullTextModel("", data.get("sort"), data["offset"], data["page"])

    for ddo in query_result[0]:
        sanitize_record(ddo)

    response = make_paginate_response(query_result, search_model, metadata)
    return Response(
        json.dumps(response, default=datetime_converter),
        200,
        content_type="application/json",
    )


###########################
# VALIDATE
###########################


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
# Since this method is public, this is just an example of how to do. You should either add some auth methods here, or protect this endpoint from your nginx
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
    ecies_private_key = os.environ.get("EVENTS_ECIES_PRIVATE_KEY", None)
    if ecies_private_key is None:
        return "no privatekey configured", 400
    try:
        ecies_account = Account.from_key(ecies_private_key)
        key = eth_keys.KeyAPI.PrivateKey(ecies_account.privateKey)
        logger.debug(f"Encrypting:{data} with {key.public_key.to_hex()}")
        encrypted_data = ecies.encrypt(key.public_key.to_hex(), data)
        logger.debug(f"Got encrypted ddo: {encrypted_data}")
        response = Response(encrypted_data)
        response.headers.set("Content-Type", "application/octet-stream")
        return response
    except Exception as e:
        logger.error(f"encrypt error:{str(e)}")
        return "Encrypt error", 500
