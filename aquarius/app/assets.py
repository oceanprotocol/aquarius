import hashlib
import json
import logging
from datetime import datetime

import pytz
from flask import Blueprint, request, Response
from oceandb_driver_interface.search_model import QueryModel, FullTextModel

from aquarius.app.dao import Dao
from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
assets = Blueprint('assets', __name__)

# Prepare OceanDB
dao = Dao(config_file=app.config['CONFIG_FILE'])


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
    asset_with_id = dao.get_assets()
    asset_ids = [a['id'] for a in asset_with_id]
    resp_body = dict({'ids': asset_ids})
    return Response(_sanitize_record(resp_body), 200, content_type='application/json')


@assets.route('/ddo/<id>', methods=['GET'])
def get_ddo(id):
    """Get DDO of a particular asset.
    ---
    tags:
      - ddo
    parameters:
      - name: id
        in: path
        description: ID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successful operation
      404:
        description: This asset ID is not in OceanDB
    """
    try:
        asset_record = dao.get(id)
        return Response(_sanitize_record(asset_record), 200, content_type='application/json')
    except Exception as e:
        logging.error(e)
        return f'{id} asset_id is not in OceanDB', 404


@assets.route('/metadata/<id>', methods=['GET'])
def get_metadata(id):
    """Get metadata of a particular asset
    ---
    tags:
      - metadata
    parameters:
      - name: id
        in: path
        description: ID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successful operation.
      404:
        description: This asset ID is not in OceanDB.
    """
    try:
        asset_record = dao.get(id)
        metadata = dict()
        i = -1
        for service in asset_record['service']:
            i = i + 1
            if service['type'] == 'Metadata':
                metadata = asset_record['service'][i]
        return Response(_sanitize_record(metadata), 200, content_type='application/json')
    except Exception as e:
        logging.error(e)
        return f'{id} asset_id is not in OceanDB', 404


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
            - publicKey
            - authentication
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
            service:
                  type: array
                  description: List of services.
                  example: [{"type": "Consume",
                             "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"},
                            {"type": "Compute",
                             "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"},
                            {"type": "Metadata",
                             "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
                             "metadata": {
                               "base": {
                                 "name": "UK Weather information 2011",
                                 "type": "dataset",
                                 "description": "Weather information of UK including temperature and humidity",
                                 "size": "3.1gb",
                                 "dateCreated": "2012-10-10T17:00:000Z",
                                 "author": "Met Office",
                                 "license": "CC-BY",
                                 "copyrightHolder": "Met Office",
                                 "encoding": "UTF-8",
                                 "compression": "zip",
                                 "contentType": "text/csv",
                                 "workExample": "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                                 "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                                 "links": [
                                   {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                                   {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                                   {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                                 ],
                                 "inLanguage": "en",
                                 "tags": "weather, uk, 2011, temperature, humidity",
                                 "price": 10

                               },
                               "curation": {
                                 "rating": 0.93,
                                 "numVotes": 123,
                                 "schema": "Binary Votting"
                               },
                               "additionalInformation" : {
                                 "updateFrecuency": "yearly",
                                 "structuredMarkup" : [
                                   { "uri" : "http://skos.um.es/unescothes/C01194/jsonld", "mediaType" : "application/ld+json"},
                                   { "uri" : "http://skos.um.es/unescothes/C01194/turtle", "mediaType" : "text/turtle"}]
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
    required_attributes = ['@context', 'id', 'publicKey', 'authentication', 'service']
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls', 'type']
    data = request.json
    if not data:
        logging.error(f'request body seems empty, expecting {required_attributes}')
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            logging.error(f'{attr} is required, got {str(data)}')
            return f'{attr} is required for registering an asset.', 400

    for service in data['service']:
        if service['type'] == 'Metadata':
            for attr in required_metadata_base_attributes:
                if attr not in service['metadata']['base']:
                    logging.error('%s metadata is required, got %s' % (
                    attr, str(service['metadata']['base'])))
                    return f'{attr} is required for registering an asset.', 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record = data
    # Index to write in the metadata service
    i = -1
    for service in _record['service']:
        i = i + 1
        if service['type'] == 'Metadata':
            _record['service'][i]['metadata']['base']['dateCreated'] = datetime.utcnow().replace(
                microsecond=0).replace(
                tzinfo=pytz.UTC).isoformat()
            _record['service'][i]['metadata']['curation']['rating'] = 0.00
            _record['service'][i]['metadata']['curation']['numVotes'] = 0
            _record['service'][i]['metadata']['additionalInformation'][
                'checksum'] = hashlib.sha3_256(
                json.dumps(service['metadata']['base']).encode('UTF-8')).hexdigest()
    try:
        dao.register(_record, data['id'])
        # add new assetId to response
        return Response(_sanitize_record(_record), 201, content_type='application/json')
    except Exception as err:
        logging.error(f'encounterd an error while saving the asset data to OceanDB: {str(err)}')
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
            - id
            - publicKey
            - authentication
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
            service:
                  type: array
                  description: List of services.
                  example: [{"type": "Consume",
                             "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"},
                            {"type": "Compute",
                             "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"},
                            {"type": "Metadata",
                             "serviceEndpoint": "http://myaquarius.org/api/v1/aquarius/assets/metadata/{did}",
                             "metadata": {
                               "base": {
                                 "name": "UK Weather information 2011",
                                 "type": "dataset",
                                 "description": "Weather information of UK including temperature and humidity",
                                 "size": "3.1gb",
                                 "dateCreated": "2012-10-10T17:00:000Z",
                                 "author": "Met Office",
                                 "license": "CC-BY",
                                 "copyrightHolder": "Met Office",
                                 "encoding": "UTF-8",
                                 "compression": "zip",
                                 "contentType": "text/csv",
                                 "workExample": "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                                 "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                                 "links": [
                                     {
                                         "name": "Sample of Asset Data",
                                         "type": "sample",
                                         "url": "https://foo.com/sample.csv"
                                     },
                                     {
                                         "name": "Data Format Definition",
                                         "type": "format",
                                         "AssetID": "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                                     }
                                 ],
                                 "inLanguage": "en",
                                 "tags": "weather, uk, 2011, temperature, humidity",
                                 "price": 10

                               },
                               "curation": {
                                 "rating": 0.93,
                                 "numVotes": 123,
                                 "schema": "Binary Voting"
                               },
                               "additionalInformation" : {
                                 "updateFrecuency": "yearly",
                                 "structuredMarkup" : [
                                   { "uri" : "http://skos.um.es/unescothes/C01194/jsonld", "mediaType" : "application/ld+json"},
                                   { "uri" : "http://skos.um.es/unescothes/C01194/turtle", "mediaType" : "text/turtle"}]
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
    required_attributes = ['@context', 'id', 'publicKey', 'authentication', 'service']
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls', 'type']
    required_metadata_curation_attributes = ['rating', 'numVotes']

    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should be formatted as a dict.'

    for attr in required_attributes:
        if attr not in data:
            return f'{attr} is required for registering an asset.', 400

    for service in data['service']:
        if service['type'] == 'Metadata':
            for attr in required_metadata_base_attributes:
                if attr not in service['metadata']['base']:
                    logging.error(
                        f'{attr} metadata is required, got {str(service["metadata"]["base"])}')
                    return f'{attr} is required for registering an asset.', 400

            for attr in required_metadata_curation_attributes:
                if attr not in service['metadata']['curation']:
                    logging.error(
                        f'{attr} metadata is required, got {str(service["metadata"]["curation"])}')
                    return f'{attr} is required for registering an asset.', 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record = data
    try:

        if dao.get(did) is None:
            register()
            return _sanitize_record(_record), 201
        else:
            # Index to write in the metadata service
            i = -1
            for service in _record['service']:
                i = i + 1
                if service['type'] == 'Metadata':
                    _record['service'][i]['metadata']['base']['dateCreated'] = _get_date(
                        dao.get(did)['service'])
                    _record['service'][i]['metadata']['additionalInformation'][
                        'checksum'] = hashlib.sha3_256(
                        json.dumps(service['metadata']['base']).encode('UTF-8')).hexdigest()
            dao.update(_record, did)
            return Response(_sanitize_record(_record), 200, content_type='application/json')
    except Exception as err:
        return f'Some error: {str(err)}', 500


@assets.route('/ddo/<id>', methods=['DELETE'])
def retire(id):
    """Retire metadata of an asset
    ---
    tags:
      - ddo
    parameters:
      - name: id
        in: path
        description: ID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successfully deleted
      404:
        description: This asset ID is not in OceanDB
      500:
        description: Error
    """
    try:
        if dao.get(id) is None:
            return 'This asset ID is not in OceanDB', 404
        else:
            dao.delete(id)
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
    assets_with_id = dao.get_assets()
    assets_metadata = {a['id']: a for a in assets_with_id}
    for i in assets_metadata:
        _sanitize_record(i)
    return Response(json.dumps(assets_metadata), 200, content_type='application/json')


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

    for i in query_result:
        _sanitize_record(i)
    return Response(json.dumps(query_result), 200, content_type='application/json')


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
    for i in query_result:
        _sanitize_record(i)
    return Response(json.dumps(query_result), 200, content_type='application/json')


@assets.route('/ddo', methods=['DELETE'])
def retire_all():
    """Retire metadata of an asset
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
        all_ids = [a['id'] for a in dao.get_assets()]
        for i in all_ids:
            dao.delete(i)
        return 'All ddo successfully deleted', 200
    except Exception as e:
        logging.error(e)
        return 'An error was found', 500


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)


def validate_asset_data(data):
    return ''


def _get_date(services):
    for i in services:
        if i['type'] == 'Metadata':
            return i['metadata']['base']['dateCreated']
