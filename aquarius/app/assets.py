#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import copy
import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from plecos.plecos import (is_valid_dict_local, is_valid_dict_remote, list_errors_dict_local,
                           list_errors_dict_remote)

from aquarius.app.dao import Dao
from aquarius.config import Config
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
assets = Blueprint('assets', __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config['CONFIG_FILE'])
logger = logging.getLogger('aquarius')

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


@assets.route('', methods=['GET'])
def get_assets():
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
    return Response(_sanitize_record(resp_body), 200, content_type='application/json')


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
        return Response(_sanitize_record(asset_record), 200, content_type='application/json')
    except Exception as e:
        logger.error(e)
        return f'{did} asset DID is not in OceanDB', 404


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
        metadata = _get_metadata(asset_record['service'])
        return Response(_sanitize_record(metadata), 200, content_type='application/json')
    except Exception as e:
        logger.error(e)
        return f'{did} asset DID is not in OceanDB', 404


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
          properties:
            "@context":
              description:
              example: https://w3id.org/did/v1
              type: string
            id:
              description: ID of the asset.
              example: did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e429
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
                  example: [{"type": "authorization",
                              "serviceEndpoint": "http://localhost:12001",
                              "service": "SecretStore",
                              "index": 0
                            },
                            {"type": "access",
                             "index": 1,
                             "serviceEndpoint":
                             "http://localhost:8030/api/v1/brizo/services/consume",
                             "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize"
                             },
                           {
                            "type": "metadata",
                            "index": 2,
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
                                    "price": "10"
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
    required_attributes = ['@context', 'created', 'id', 'publicKey', 'authentication', 'proof',
                           'service']
    data = request.json
    if not data:
        logger.error(f'request body seems empty.')
        return 400
    msg, status = check_required_attributes(required_attributes, data, 'register')
    if msg:
        return msg, status
    msg, status = check_no_urls_in_files(_get_main_metadata(data['service']), 'register')
    if msg:
        return msg, status
    msg, status = validate_date_format(data['created'])
    if status:
        return msg, status
    _record = dict()
    _record = copy.deepcopy(data)
    _record['created'] = datetime.strptime(data['created'], DATETIME_FORMAT)
    for service in _record['service']:
        if service['type'] == 'metadata':
            service_id = int(service['index'])
            if Config(filename=app.config['CONFIG_FILE']).allow_free_assets_only == 'true':
                if _record['service'][service_id]['attributes']['main']['price'] != "0":
                    logger.warning('Priced assets are not supported in this marketplace')
                    return 'Priced assets are not supported in this marketplace', 400
            _record['service'][service_id]['attributes']['main']['dateCreated'] = \
                datetime.strptime(
                    _record['service'][service_id]['attributes']['main']['dateCreated'],
                    DATETIME_FORMAT
                )
            _record['service'][service_id]['attributes']['main']['datePublished'] = \
                datetime.strptime(get_timestamp(), DATETIME_FORMAT)

            _record['service'][service_id]['attributes']['curation'] = {}
            _record['service'][service_id]['attributes']['curation']['rating'] = 0.00
            _record['service'][service_id]['attributes']['curation']['numVotes'] = 0
            _record['service'][service_id]['attributes']['curation']['isListed'] = True
    _record['service'] = _reorder_services(_record['service'])

    if not is_valid_dict_remote(_get_metadata(_record['service'])['attributes']):
        logger.error(
            _list_errors(list_errors_dict_remote,
                         _get_metadata(_record['service'])['attributes']))
        return jsonify(_list_errors(list_errors_dict_remote,
                                    _get_metadata(_record['service'])['attributes'])), 400

    try:
        dao.register(_record, data['id'])
        # add new assetId to response
        return Response(_sanitize_record(_record), 201, content_type='application/json')
    except Exception as err:
        logger.error(f'encounterd an error while saving the asset data to OceanDB: {str(err)}')
        return f'Some error: {str(err)}', 500


@assets.route('/ddo/<did>', methods=['PUT'])
def update(did):
    """Update DDO of an existing asset
    ---
    tags:
      - ddo
    consumes:
      - application/json
    parameters:
      - name: did
        in: path
        description: DID of the asset.
        required: true
        type: string
      - in: body
        name: body
        required: true
        description: DDO of the asset.
        schema:
          type: object
          required:
            - "@context"
            - created
            - id
            - publicKey
            - authentication
            - proof
            - service
          properties:
            "@context":
              description:
              example: https://w3id.org/did/v1
              type: string
            id:
              description: ID of the asset.
              example: did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e429
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
                             "signatureValue": "0xbd7b46b3ac664167bc70ac211b1a1da0baed9ead91613a
                                                5f02dfc25c1bb6e3ff40861b455017e8a587fd4e37b70343
                                                6072598c3a81ec88be28bfe33b61554a471b"
                            }
            service:
                  type: array
                  description: List of services.
                  example: [{"type": "access",
                             "index": 1,
                             "serviceEndpoint": "http://localhost:8030/api/v1/brizo/services/consume",
                             "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize"},
                            {"type": "authorization",
                              "serviceEndpoint": "http://localhost:12001",
                              "service": "SecretStore",
                              "index": 0
                            },
                           {
                            "type": "metadata",
                            "index": 2,
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
                                    "price": "10"
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
                                    "links": [{
                                            "name": "Sample of Asset Data",
                                            "type": "sample",
                                            "url": "https://foo.com/sample.csv"
                                        }
                                    ],
                                    "workExample": "stationId,latitude,longitude,datetime,
                                                    temperature,humidity/n423432fsd,51.509865,-0.118092,
                                                    2011-01-01T10:55:11+00:00,7.2,68",
                                    "inLanguage": "en",
                                    "copyrightHolder": "Met Office",
                                    "tags": ["weather", "uk", "2011", "temperature", "humidity"]
                                }
                            }
                        }]
    responses:
      200:
        description: Asset successfully updated.
      201:
        description: Asset successfully registered.
      400:
        description: One of the required attributes is missing.
      404:
        description: Invalid asset data.
      500:
        description: Error
    """
    required_attributes = ['@context', 'created', 'id', 'publicKey', 'authentication', 'proof',
                           'service']
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        logger.error(f'request body seems empty, expecting {required_attributes}')
        return 400
    msg, status = check_required_attributes(required_attributes, data, 'update')
    if msg:
        return msg, status
    msg, status = check_no_urls_in_files(_get_main_metadata(data['service']), 'register')
    if msg:
        return msg, status
    msg, status = validate_date_format(data['created'])
    if msg:
        return msg, status
    _record = dict()
    _record = copy.deepcopy(data)
    _record['created'] = format_timestamp(data['created'])
    _record['service'] = _reorder_services(_record['service'])
    services = {s['type']: s for s in _record['service']}
    metadata_main = services['metadata']['attributes']['main']
    metadata_main['dateCreated'] = format_timestamp(metadata_main['dateCreated'])
    metadata_main['datePublished'] = format_timestamp(metadata_main['datePublished'])
    if not is_valid_dict_remote(_get_metadata(_record['service'])['attributes']):
        logger.error(_list_errors(list_errors_dict_remote,
                                  _get_metadata(_record['service'])['attributes']))
        return jsonify(_list_errors(list_errors_dict_remote,
                                    _get_metadata(_record['service'])['attributes'])), 400

    try:
        if dao.get(did) is None:
            register()
            return _sanitize_record(_record), 201
        else:
            for service in _record['service']:
                if service['type'] == 'metadata':
                    if Config(filename=app.config['CONFIG_FILE']).allow_free_assets_only == 'true':
                        if _record['service'][0]['attributes']['main']['price'] != "0":
                            logger.warning('Priced assets are not supported in this marketplace')
                            return 'Priced assets are not supported in this marketplace', 400
            dao.update(_record, did)
            return Response(_sanitize_record(_record), 200, content_type='application/json')
    except Exception as err:
        return f'Some error: {str(err)}', 500


@assets.route('/ddo/<did>', methods=['DELETE'])
def retire(did):
    """Retire metadata of an asset
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
        description: successfully deleted
      404:
        description: This asset DID is not in OceanDB
      500:
        description: Error
    """
    try:
        if dao.get(did) is None:
            return 'This asset DID is not in OceanDB', 404
        else:
            dao.delete(did)
            return 'Succesfully deleted', 200
    except Exception as err:
        return f'Some error: {str(err)}', 500


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
    args = []
    query = dict()
    args.append(query)
    assets_with_id = dao.get_all_listed_assets()
    assets_metadata = {a['id']: a for a in assets_with_id}
    for i in assets_metadata:
        _sanitize_record(i)
    return Response(json.dumps(assets_metadata, default=_my_converter), 200,
                    content_type='application/json')


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
    assert isinstance(data, dict), 'invalid `args` type, should already formatted into a dict.'
    search_model = FullTextModel(text=data.get('text', None),
                                 sort=None if data.get('sort', None) is None else json.loads(
                                     data.get('sort', None)),
                                 offset=int(data.get('offset', 100)),
                                 page=int(data.get('page', 1)))
    query_result = dao.query(search_model)
    for i in query_result[0]:
        _sanitize_record(i)

    response = _make_paginate_response(query_result, search_model)
    return Response(json.dumps(response, default=_my_converter), 200,
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
    assert isinstance(data, dict), 'invalid `body` type, should be formatted as a dict.'
    if 'query' in data:
        search_model = QueryModel(query=data.get('query'), sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 1))
    else:
        search_model = QueryModel(query={}, sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 1))
    query_result = dao.query(search_model)
    for i in query_result[0]:
        _sanitize_record(i)

    response = _make_paginate_response(query_result, search_model)
    return Response(json.dumps(response, default=_my_converter), 200,
                    content_type='application/json')


@assets.route('/ddo', methods=['DELETE'])
def retire_all():
    """Retire metadata of all the assets.
    ---
    tags:
      - ddo
    responses:
      200:
        description: successfully deleted
      500:
        description: Error
    """
    try:
        all_ids = [a['id'] for a in dao.get_all_assets()]
        for i in all_ids:
            dao.delete(i)
        return 'All ddo successfully deleted', 200
    except Exception as e:
        logger.error(e)
        return 'An error was found', 500


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
    assert isinstance(data, dict), 'invalid `body` type, should be formatted as a dict.'

    if is_valid_dict_local(data):
        return jsonify(True)
    else:
        res = jsonify(_list_errors(list_errors_dict_local, data))
        return res


def _list_errors(list_errors_function, data):
    error_list = list()
    for err in list_errors_function(data):
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        this_err_response = {'path': "/".join(stack_path), 'message': err[1].message}
        error_list.append(this_err_response)
    return error_list


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record, default=_my_converter)


def check_required_attributes(required_attributes, data, method):
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'
    logger.info('got %s request: %s' % (method, data))
    if not data:
        logger.error('%s request failed: data is empty.' % method)
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400

    for attr in required_attributes:
        if attr not in data:
            logger.error('%s request failed: required attr %s missing.' % (method, attr))
            return '"%s" is required in the call to %s' % (attr, method), 400

    return None, None


def check_no_urls_in_files(main, method):
    if 'files' in main:
        for file in main['files']:
            if 'url' in file:
                logger.error('%s request failed: url is not allowed in files ' % method)
                return '%s request failed: url is not allowed in files ' % method, 400
    return None, None


def _get_metadata(services):
    for service in services:
        if service['type'] == 'metadata':
            return service


def _get_main_metadata(services):
    return _get_metadata(services)['attributes']['main']


def _get_curation_metadata(services):
    return _get_metadata(services)['attributes']['curation']


def get_timestamp():
    """Return the current system timestamp."""
    return f'{datetime.utcnow().replace(microsecond=0).isoformat()}Z'


def format_timestamp(timestamp):
    return f'{datetime.strptime(timestamp, DATETIME_FORMAT).replace(microsecond=0).isoformat()}Z'


def validate_date_format(date):
    try:
        datetime.strptime(date, DATETIME_FORMAT)
        return None, None
    except Exception as e:
        logging.error(str(e))
        return f"Incorrect data format, should be '{DATETIME_FORMAT}'", 400


def _my_converter(o):
    if isinstance(o, datetime):
        return o.strftime(DATETIME_FORMAT)


def _make_paginate_response(query_list_result, search_model):
    total = query_list_result[1]
    offset = search_model.offset
    result = dict()
    result['results'] = query_list_result[0]
    result['page'] = search_model.page

    result['total_pages'] = int(total / offset) + int(total % offset > 0)
    result['total_results'] = total
    return result


def _reorder_services(services):
    result = []
    for service in services:
        if service['type'] == 'metadata':
            result.append(service)

    for service in services:
        if service['type'] != 'metadata':
            result.append(service)

    return result
