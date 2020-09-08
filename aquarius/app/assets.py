#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import json
import logging

from flask import Blueprint, jsonify, request, Response
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from plecos.plecos import (
    is_valid_dict_local,
    is_valid_dict_remote,
    list_errors_dict_local,
    list_errors_dict_remote,
)

from aquarius.app.dao import Dao
from aquarius.app.util import (
    make_paginate_response,
    datetime_converter,
    get_metadata_from_services,
    sanitize_record,
    list_errors,
    validate_data,
    init_new_ddo)
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
assets = Blueprint('assets', __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config['CONFIG_FILE'])
logger = logging.getLogger('aquarius')


###########################
# CREATE
###########################

@assets.route('/ddo', methods=['POST'])
def register():
    """Register DDO of a new asset
    ---
    tags:
      - ddo
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: DDO of the asset.
        schema:
          type: object
          required:
            - "@context"
            - id
            - created
            - publicKey
            - authentication
            - proof
            - service
            - dataToken
          properties:
            "@context":
              description:
              example: https://w3id.org/did/v1
              type: string
            id:
              description: ID of the asset.
              example: did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e429
              type: string
            dataToken:
              description: dataToken  of the asset.
              example: 0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687
              type: string
            created:
              description: date of ddo creation.
              example: "2016-02-08T16:02:20Z"
              type: string
            publicKey:
                  type: array
                  description: List of public keys.
                  example: [{"id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
                            "type": "EthereumECDSAKey",
                            "owner": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e"}]
            authentication:
                  type: array
                  description: List of authentication mechanisms.
                  example: [{"type": "RsaSignatureAuthentication2018",
                            "publicKey": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430"}]
            proof:
                  type: dictionary
                  description: Information about the creation and creator of the asset.
                  example:  {"type": "DDOIntegritySignature",
                             "created": "2016-02-08T16:02:20Z",
                             "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
                             "signatureValue": "0xbd7b46b3ac664167bc70ac211b1a1da0baed9ead91613a5
                                                f02dfc25c1bb6e3ff40861b455017e8a587fd4e37b7034360
                                                72598c3a81ec88be28bfe33b61554a471b"
                            }
            service:
                  type: array
                  description: List of services.
                  example: [
                            {"type": "access",
                             "index": 0,
                             "serviceEndpoint":
                             "http://localhost:8030/api/v1/brizo/services/consume",
                             "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize",
                             "attributes": {
                                 "main": {
                                    "cost":"10",
                                    "timeout":"0",
                                }
                              }
                             },
                           {
                            "type": "metadata",
                            "index": 1,
                            "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/did:op
                                                :0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
                            "attributes": {
                                "main": {
                                    "name": "UK Weather information 2011",
                                    "type": "dataset",
                                    "dateCreated": "2012-02-01T10:55:11Z",
                                    "author": "Met Office",
                                    "license": "CC-BY",
                                    "files": [{
                                            "contentLength": "4535431",
                                            "contentType": "text/csv",
                                            "encoding": "UTF-8",
                                            "compression": "zip",
                                            "index" :0,
                                            "resourceId":
                                            "access-log2018-02-13-15-17-29-18386C502CAEA932"
                                    }
                                    ],
                                },
                                "encryptedFiles": "0x098213xzckasdf089723hjgdasfkjgasfv",
                                "curation": {
                                    "rating": 0.93,
                                    "numVotes": 123,
                                    "schema": "Binary Voting"
                                },
                                "additionalInformation": {
                                    "description": "Weather information of UK including
                                                    temperature and humidity",
                                    "copyrightHolder": "Met Office",
                                    "workExample": "stationId,latitude,longitude,datetime,
                                                    temperature,humidity/n423432fsd,51.509865,-0.118092,
                                                    2011-01-01T10:55:11+00:00,7.2,68",
                                    "inLanguage": "en",
                                    "links": [{
                                            "name": "Sample of Asset Data",
                                            "type": "sample",
                                            "url": "https://foo.com/sample.csv"
                                        }
                                    ],
                                    "tags": ["weather", "uk", "2011", "temperature", "humidity"]
                                }
                            }
                        }]
    responses:
      201:
        description: Asset successfully registered.
      400:
        description: One of the required attributes is missing.
      404:
        description: Invalid asset data.
      500:
        description: Error
    """
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        logger.error(f'request body seems empty.')
        return 400
    msg, status = validate_data(data,'register')
    if msg:
        return msg, status
    
    _record = init_new_ddo(data)
    if not is_valid_dict_remote(get_metadata_from_services(_record['service'])['attributes']):
        errors = list_errors(list_errors_dict_remote,
                             get_metadata_from_services(_record['service'])['attributes'])
        logger.error(errors)
        return jsonify(errors), 400

    try:
        dao.register(_record, data['id'])
        # add new assetId to response
        return Response(sanitize_record(_record), 201, content_type='application/json')
    except (KeyError, Exception) as err:
        logger.error(
            f'encountered an error while saving the asset data to OceanDB: {str(err)}')
        return f'Some error: {str(err)}', 500


###########################
# GETTERS
###########################

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
    data = request.args
    assert isinstance(
        data, dict), 'invalid `args` type, should already formatted into a dict.'
    search_model = FullTextModel(text=data.get('text', None),
                                 sort=None if data.get('sort', None) is None else json.loads(
                                     data.get('sort', None)),
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
