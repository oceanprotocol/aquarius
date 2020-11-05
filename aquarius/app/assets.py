#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import os

from flask import Blueprint, jsonify, request, Response
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.web3_provider import Web3Provider
from ocean_lib.ocean.util import get_web3_connection_provider
from ocean_lib.config import Config as OceanConfig
from plecos.plecos import (
    is_valid_dict_local,
    list_errors_dict_local,
)

from aquarius.app.auth_util import has_update_request_permission, get_signer_address
from aquarius.app.dao import Dao
from aquarius.app.util import (
    make_paginate_response,
    datetime_converter,
    get_metadata_from_services,
    sanitize_record,
    list_errors,
    get_request_data)
from aquarius.events.metadata_updater import MetadataUpdater
from aquarius.events.util import get_artifacts_path
from aquarius.log import setup_logging
from aquarius.myapp import app

ConfigProvider.set_config(OceanConfig(app.config['CONFIG_FILE']))
Web3Provider.init_web3(provider=get_web3_connection_provider(os.environ.get('EVENTS_RPC', '')))
ContractHandler.set_artifacts_path(get_artifacts_path())

setup_logging()
assets = Blueprint('assets', __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config['CONFIG_FILE'])
logger = logging.getLogger('aquarius')


@assets.route('', methods=['GET'])
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
    asset_ids = [a['id'] for a in asset_with_id]
    resp_body = dict({'ids': asset_ids})
    return Response(sanitize_record(resp_body), 200, content_type='application/json')


@assets.route('/ddo/<did>', methods=['GET'])
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
        return Response(sanitize_record(asset_record), 200, content_type='application/json')
    except Exception as e:
        logger.error(f'get_ddo: {str(e)}')
        return f'{did} asset DID is not in OceanDB', 404


@assets.route('/ddo', methods=['GET'])
def get_asset_ddos():
    """Get DDO of all assets.
    ---
    tags:
      - ddo
    responses:
      200:
        description: successful action
    """
    assets_with_id = dao.get_all_listed_assets()
    assets_metadata = {a['id']: a for a in assets_with_id}
    for _, _record in assets_metadata.items():
        sanitize_record(_record)
    return Response(json.dumps(assets_metadata, default=datetime_converter), 200,
                    content_type='application/json')


@assets.route('/metadata/<did>', methods=['GET'])
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
        metadata = get_metadata_from_services(asset_record['service'])
        return Response(sanitize_record(metadata), 200, content_type='application/json')
    except Exception as e:
        logger.error(f'get_metadata: {str(e)}')
        return f'{did} asset DID is not in OceanDB', 404


###########################
# SEARCH
###########################

@assets.route('/ddo/query', methods=['GET'])
def query_text():
    """Get a list of DDOs that match with the given text.
    ---
    tags:
      - ddo
    parameters:
      - name: text
        in: query
        description: ID of the asset.
        required: true
        type: string
      - name: sort
        in: query
        type: object
        description: Key or list of keys to sort the result
        example: {"value":1}
      - name: offset
        in: query
        type: int
        description: Number of records per page
        example: 100
      - name: page
        in: query
        type: int
        description: Page showed
        example: 1
    responses:
      200:
        description: successful action
    """
    data = get_request_data(request)
    assert isinstance(
        data, dict), 'invalid `args` type, should already formatted into a dict.'
    sort = data.get('sort', None)
    if sort is not None and isinstance(sort, str):
        sort = json.loads(sort)

    search_model = FullTextModel(text=data.get('text', None),
                                 sort=sort,
                                 offset=int(data.get('offset', 100)),
                                 page=int(data.get('page', 1)))
    query_result = dao.query(search_model)
    for i in query_result[0]:
        sanitize_record(i)

    response = make_paginate_response(query_result, search_model)
    return Response(json.dumps(response, default=datetime_converter), 200,
                    content_type='application/json')


@assets.route('/ddo/query', methods=['POST'])
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
    """
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    assert isinstance(
        data, dict), 'invalid `body` type, should be formatted as a dict.'
    if 'query' in data:
        search_model = QueryModel(query=data.get('query'), sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 1))
    else:
        search_model = QueryModel(query={}, sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 1))
    query_result = dao.query(search_model)
    for ddo in query_result[0]:
        sanitize_record(ddo)

    response = make_paginate_response(query_result, search_model)
    return Response(json.dumps(response, default=datetime_converter), 200,
                    content_type='application/json')


###########################
# VALIDATE
###########################

@assets.route('/ddo/validate', methods=['POST'])
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
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    assert isinstance(
        data, dict), 'invalid `body` type, should be formatted as a dict.'

    if is_valid_dict_local(data):
        return jsonify(True)
    else:
        res = jsonify(list_errors(list_errors_dict_local, data))
        return res


@assets.route('/ddo/update/<did>', methods=['PUT'])
def update_ddo_info(did):
    """
    Update daoo dao record.

    Args:
        did: (str): write your description
    """
    assert request.json and isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    address = data.get('adminAddress', None)
    if not address or not has_update_request_permission(address):
        return jsonify(error=f'Unauthorized.'), 401

    _address = None
    signature = data.get('signature', None)
    if signature:
        _address = get_signer_address(address, signature, logger)

    if not _address or _address.lower() != address.lower():
        return jsonify(error=f'Unauthorized.'), 401

    try:
        asset_record = dao.get(did)
        if not asset_record:
            return jsonify(error=f'Asset {did} not found.'), 404

        updater = MetadataUpdater(oceandb=dao.oceandb, web3=Web3Provider.get_web3(), config=ConfigProvider.get_config())
        updater.do_single_update(asset_record)

        return jsonify('acknowledged.'), 200
    except Exception as e:
        logger.error(f'get_metadata: {str(e)}')
        return f'{did} asset DID is not in OceanDB', 404


@assets.route('/ddo/<did>', methods=['DELETE'])
def delist_ddo(did):
    """
    Delist a dao did.

    Args:
        did: (str): write your description
    """
    assert request.json and isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    address = data.get('adminAddress', None)
    if not address or not has_update_request_permission(address):
        return jsonify(error=f'Unauthorized.'), 401

    _address = None
    signature = data.get('signature', None)
    if signature:
        _address = get_signer_address(address, signature, logger)

    if not _address or _address.lower() != address.lower():
        return jsonify(error=f'Unauthorized.'), 401

    try:
        asset_record = dao.get(did)
        if not asset_record:
            return jsonify(error=f'Asset {did} not found.'), 404

        updater = MetadataUpdater(oceandb=dao.oceandb, web3=Web3Provider.get_web3(), config=ConfigProvider.get_config())
        updater.do_single_update(asset_record)

        return jsonify('acknowledged.'), 200
    except Exception as e:
        logger.error(f'get_metadata: {str(e)}')
        return f'{did} asset DID is not in OceanDB', 404
