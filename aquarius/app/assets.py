#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import copy
import json
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from plecos.plecos import is_valid_dict, list_errors_dict_local

from aquarius.app.dao import Dao
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
assets = Blueprint('assets', __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config['CONFIG_FILE'])
logger = logging.getLogger('aquarius')


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
    args = []
    query = dict()
    args.append(query)
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
              example: https://w3id.org/future-method/v1
              type: string
            id:
              description: ID of the asset.
              example: did:op:123456789abcdefghi
              type: string
            created:
              description: date of ddo creation.
              example: "2016-02-08T16:02:20Z"
              type: string
            publicKey:
                  type: array
                  description: List of public keys.
                  example: [{"id": "did:op:123456789abcdefghi#keys-1"},
                            {"type": "Ed25519VerificationKey2018"},
                            {"owner": "did:op:123456789abcdefghi"},
                            {"publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"}]
            authentication:
                  type: array
                  description: List of authentication mechanisms.
                  example: [{"type": "RsaSignatureAuthentication2018"},
                            {"publicKey": "did:op:123456789abcdefghi#keys-1"}]
            proof:
                  type: dictionary
                  description: Information about the creation and creator of the asset.
                  example:  {"type": "UUIDSignature",
                             "created": "2016-02-08T16:02:20Z",
                             "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
                             "signatureValue": "QNB13Y7Q9...1tzjn4w=="
                            }
            service:
                  type: array
                  description: List of services.
                  example: [{"type": "Access",
                             "serviceEndpoint":
                             "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${
                             pubKey}&serviceId={serviceId}&url={url}"},
                            {"type": "Compute",
                             "serviceEndpoint":
                             "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${
                             pubKey}&serviceId={serviceId}&algo={algo}&container={container}"},
                           {
                            "type": "Metadata",
                            "serviceDefinitionId": "2",
                            "serviceEndpoint":
                            "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
                            "metadata": {
                                "base": {
                                    "name": "UK Weather information 2011",
                                    "type": "dataset",
                                    "description": "Weather information of UK including
                                    temperature and humidity",
                                    "dateCreated": "2012-02-01T10:55:11Z",
                                    "author": "Met Office",
                                    "license": "CC-BY",
                                    "copyrightHolder": "Met Office",
                                    "compression": "zip",
                                    "workExample": "stationId,latitude,longitude,datetime,
                                    temperature,humidity/n423432fsd,51.509865,-0.118092,
                                    2011-01-01T10:55:11+00:00,7.2,68",
                                    "files": [{
                                            "contentLength": "4535431",
                                            "contentType": "text/csv",
                                            "encoding": "UTF-8",
                                            "compression": "zip",
                                            "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                                    }
                                    ],
                                    "encryptedFiles": "0x098213xzckasdf089723hjgdasfkjgasfv",
                                    "links": [{
                                            "name": "Sample of Asset Data",
                                            "type": "sample",
                                            "url": "https://foo.com/sample.csv"
                                        },
                                        {
                                            "name": "Data Format Definition",
                                            "type": "format",
                                            "AssetID":
                                            "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                                        }
                                    ],
                                    "inLanguage": "en",
                                    "tags": "weather, uk, 2011, temperature, humidity",
                                    "price": 10,
                                    "checksum":
                                    "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85262"
                                },
                                "curation": {
                                    "rating": 0.93,
                                    "numVotes": 123,
                                    "schema": "Binary Voting"
                                },
                                "additionalInformation": {
                                    "updateFrecuency": "yearly",
                                    "structuredMarkup": [{
                                            "uri": "http://skos.um.es/unescothes/C01194/jsonld",
                                            "mediaType": "application/ld+json"
                                        },
                                        {
                                            "uri": "http://skos.um.es/unescothes/C01194/turtle",
                                            "mediaType": "text/turtle"
                                        }
                                    ]
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
    required_metadata_base_attributes = ['name', 'dateCreated', 'author', 'license',
                                         'price', 'encryptedFiles', 'type', 'checksum']
    data = request.json
    if not data:
        logger.error(f'request body seems empty, expecting {required_attributes}')
        return 400
    msg, status = check_required_attributes(required_attributes, data, 'register')
    if msg:
        return msg, status
    msg, status = check_required_attributes(required_metadata_base_attributes,
                                            _get_base_metadata(data['service']), 'register')
    if msg:
        return msg, status
    msg, status = check_no_urls_in_files(_get_base_metadata(data['service']), 'register')
    if msg:
        return msg, status
    msg, status = _validate_date_format(data['created'])
    if status:
        return msg, status
    _record = dict()
    _record = copy.deepcopy(data)
    _record['created'] = datetime.strptime(data['created'], '%Y-%m-%dT%H:%M:%SZ')
    for service in _record['service']:
        if service['type'] == 'Metadata':
            service_id = int(service['serviceDefinitionId'])
            _record['service'][service_id]['metadata']['base']['datePublished'] = \
                datetime.strptime(f'{datetime.utcnow().replace(microsecond=0).isoformat()}Z',
                                  '%Y-%m-%dT%H:%M:%SZ')
            _record['service'][service_id]['metadata']['curation'] = {}
            _record['service'][service_id]['metadata']['curation']['rating'] = 0.00
            _record['service'][service_id]['metadata']['curation']['numVotes'] = 0
            _record['service'][service_id]['metadata']['curation']['isListed'] = True
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
              example: https://w3id.org/future-method/v1
              type: string
            id:
              description: ID of the asset.
              example: did:op:123456789abcdefghi
              type: string
            created:
              description: date of ddo creation.
              example: "2016-02-08T16:02:20Z"
              type: string
            publicKey:
                  type: array
                  description: List of public keys.
                  example: [{"id": "did:op:123456789abcdefghi#keys-1"},
                            {"type": "Ed25519VerificationKey2018"},
                            {"owner": "did:op:123456789abcdefghi"},
                            {"publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"}]
            authentication:
                  type: array
                  description: List of authentication mechanisms.
                  example: [{"type": "RsaSignatureAuthentication2018"},
                            {"publicKey": "did:op:123456789abcdefghi#keys-1"}]
            proof:
                  type: dictionary
                  description: Information about the creation and creator of the asset.
                  example:  {"type": "UUIDSignature",
                             "created": "2016-02-08T16:02:20Z",
                             "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
                             "signatureValue": "QNB13Y7Q9...1tzjn4w=="
                            }
            service:
                  type: array
                  description: List of services.
                  example: [{"type": "Access",
                             "serviceEndpoint":
                             "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${
                             pubKey}&serviceId={serviceId}&url={url}"},
                            {"type": "Compute",
                             "serviceEndpoint":
                             "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${
                             pubKey}&serviceId={serviceId}&algo={algo}&container={container}"},
                           {
                            "type": "Metadata",
                            "serviceDefinitionId": "2",
                            "serviceEndpoint":
                            "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
                            "metadata": {
                                "base": {
                                    "name": "UK Weather information 2011",
                                    "type": "dataset",
                                    "description": "Weather information of UK including
                                    temperature and humidity",
                                    "dateCreated": "2012-02-01T10:55:11Z",
                                    "author": "Met Office",
                                    "license": "CC-BY",
                                    "copyrightHolder": "Met Office",
                                    "compression": "zip",
                                    "workExample": "stationId,latitude,longitude,datetime,
                                    temperature,humidity/n423432fsd,51.509865,-0.118092,
                                    2011-01-01T10:55:11+00:00,7.2,68",
                                    "files": [{
                                            "contentLength": "4535431",
                                            "contentType": "text/csv",
                                            "encoding": "UTF-8",
                                            "compression": "zip",
                                            "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                                    }
                                    ],

                                    "encryptedFiles": "0x098213xzckasdf089723hjgdasfkjgasfv",
                                    "links": [{
                                            "name": "Sample of Asset Data",
                                            "type": "sample",
                                            "url": "https://foo.com/sample.csv"
                                        },
                                        {
                                            "name": "Data Format Definition",
                                            "type": "format",
                                            "AssetID":
                                            "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                                        }
                                    ],
                                    "inLanguage": "en",
                                    "tags": "weather, uk, 2011, temperature, humidity",
                                    "price": 10,
                                    "checksum":
                                    "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85262"
                                },
                                "curation": {
                                    "rating": 0.93,
                                    "numVotes": 123,
                                    "schema": "Binary Voting"
                                },
                                "additionalInformation": {
                                    "updateFrecuency": "yearly",
                                    "structuredMarkup": [{
                                            "uri": "http://skos.um.es/unescothes/C01194/jsonld",
                                            "mediaType": "application/ld+json"
                                        },
                                        {
                                            "uri": "http://skos.um.es/unescothes/C01194/turtle",
                                            "mediaType": "text/turtle"
                                        }
                                    ]
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
    required_metadata_base_attributes = ['name', 'dateCreated', 'author', 'license',
                                         'price', 'encryptedFiles', 'type', 'checksum']
    required_metadata_curation_attributes = ['rating', 'numVotes']

    assert isinstance(request.json, dict), 'invalid payload format.'

    data = request.json
    if not data:
        logger.error(f'request body seems empty, expecting {required_attributes}')
        return 400
    msg, status = check_required_attributes(required_attributes, data, 'update')
    if msg:
        return msg, status
    msg, status = check_required_attributes(required_metadata_base_attributes,
                                            _get_base_metadata(data['service']), 'update')
    if msg:
        return msg, status
    msg, status = check_required_attributes(required_metadata_curation_attributes,
                                            _get_curation_metadata(data['service']), 'update')
    if msg:
        return msg, status
    msg, status = check_no_urls_in_files(_get_base_metadata(data['service']), 'register')
    if msg:
        return msg, status
    msg, status = _validate_date_format(data['created'])
    if msg:
        return msg, status

    _record = dict()
    _record = copy.deepcopy(data)
    _record['created'] = datetime.strptime(data['created'], '%Y-%m-%dT%H:%M:%SZ')
    try:

        if dao.get(did) is None:
            register()
            return _sanitize_record(_record), 201
        else:
            for service in _record['service']:
                service_id = int(service['serviceDefinitionId'])
                if service['type'] == 'Metadata':
                    _record['service'][service_id]['metadata']['base']['datePublished'] = _get_date(
                        dao.get(did)['service'])
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
        example: 0
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
                                 page=int(data.get('page', 0)))
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
              example: 0
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
                                  page=data.get('page', 0))
    else:
        search_model = QueryModel(query={}, sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 0))
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
    if is_valid_dict(data):
        return jsonify(True)
    else:
        error_list = list()
        for err in list_errors_dict_local(data):
            stack_path = list(err[1].relative_path)
            stack_path = [str(p) for p in stack_path]
            this_err_response = {'path': "/".join(stack_path), 'message': err[1].message}
            error_list.append(this_err_response)
        res = jsonify(error_list)
        return res


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record, default=_my_converter)


def check_required_attributes(required_attributes, data, method):
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'
    logger.info('got %s request: %s' % (method, data))
    if not data:
        logger.error('%s request failed: data is empty.' % method)
        return 'payload seems empty.', 400
    for attr in required_attributes:
        if attr not in data:
            logger.error('%s request failed: required attr %s missing.' % (method, attr))
            return '"%s" is required in the call to %s' % (attr, method), 400
    return None, None


def check_no_urls_in_files(base, method):
    if 'files' in base:
        for file in base['files']:
            if 'url' in file:
                logger.error('%s request failed: url is not allowed in files ' % method)
                return '%s request failed: url is not allowed in files ' % method, 400
    return None, None


def _get_metadata(services):
    for service in services:
        if service['type'] == 'Metadata':
            return service


def _get_base_metadata(services):
    return _get_metadata(services)['metadata']['base']


def _get_curation_metadata(services):
    return _get_metadata(services)['metadata']['curation']


def _get_date(services):
    return _get_metadata(services)['metadata']['base']['datePublished']


def _validate_date_format(date):
    try:
        datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
        return None, None
    except Exception:
        return "Incorrect data format, should be '%Y-%m-%dT%H:%M:%SZ'", 400


def _my_converter(o):
    if isinstance(o, datetime):
        return o.strftime('%Y-%m-%dT%H:%M:%SZ')


def _make_paginate_response(query_list_result, search_model):
    result = dict()
    result['results'] = query_list_result[0]
    result['page'] = search_model.page
    result['total_pages'] = int(len(query_list_result) / search_model.offset) + 1
    result['total_results'] = query_list_result[1]
    return result
