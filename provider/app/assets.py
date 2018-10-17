import hashlib
import json
import logging
from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request
from oceandb_driver_interface.search_model import QueryModel, FullTextModel
from squid_py.acl import decode
from squid_py.config import Config
from squid_py.ocean import Ocean

from provider.app.dao import Dao
from provider.app.filters import Filters
from provider.app.osmosis import generate_sasurl
from provider.constants import BaseURLs
from provider.log import setup_logging
from provider.myapp import app
from provider.constants import ConfigSections

setup_logging()
assets = Blueprint('assets', __name__)

config_file = app.config['CONFIG_FILE']
config = Config(filename=config_file)
# Prepare keeper contracts for on-chain access control
# Prepare OceanDB
dao = Dao(config_file=config_file)
provider_url = config.provider_url
provider_url += BaseURLs.ASSETS_URL
provider_address = None if not config.get(ConfigSections.KEEPER_CONTRACTS, 'provider.address') else config.get(ConfigSections.KEEPER_CONTRACTS,
                                                                                                  'provider.address')
ocn = Ocean(config_file=config_file)


def get_provider_address_filter():
    account = ocn.web3.eth.accounts[0] if not config.get(ConfigSections.KEEPER_CONTRACTS, 'provider.address') \
        else config.get(ConfigSections.KEEPER_CONTRACTS, 'provider.address')
    return {"address": account}


filters = Filters(ocean_contracts_wrapper=ocn, config_file=config_file, api_url=provider_url)
filter_access_consent = ocn.helper.watch_event(ocn.contracts.auth.contract,
                                               'AccessConsentRequested',
                                               filters.commit_access_request,
                                               0.2,
                                               fromBlock='latest',
                                               filters=get_provider_address_filter())

filter_payment = ocn.helper.watch_event(ocn.contracts.market.contract,
                                        'PaymentReceived',
                                        filters.publish_encrypted_token,
                                        0.2,
                                        fromBlock='latest',
                                        filters=get_provider_address_filter())


@assets.route('', methods=['GET'])
def get_assets():
    """Get all assets ids.
    ---
    tags:
      - assets
    responses:
      200:
        description: successful action
    """
    args = []
    query = dict()
    args.append(query)
    asset_with_id = dao.get_assets()
    asset_ids = [a['assetId'] for a in asset_with_id]
    resp_body = dict({'assetsIds': asset_ids})
    return jsonify(resp_body), 200


@assets.route('/metadata/<asset_id>', methods=['GET'])
def get(asset_id):
    """Get metadata of a particular asset
    ---
    tags:
      - assets
    parameters:
      - name: asset_id
        in: path
        description: ID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successful operation
      404:
        description: This asset id is not in OceanDB
    """
    try:
        asset_record = dao.get(asset_id)
        return jsonify(asset_record), 200
    except Exception as e:
        return '"%s asset_id is not in OceanDB' % asset_id, 404


@assets.route('/metadata', methods=['POST'])
def register():
    """Register metadata of a new asset
    ---
    tags:
      - assets
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        description: Asset metadata.
        schema:
          type: object
          required:
            - assetId
            - publisherId
            - base
          properties:
            assetId:
              description: ID of the asset.
              example: '0x1298371984723941'
              type: string
            publisherId:
              description: Id of the asset's publisher.
              type: string
              example: '0x0234242345'
            base:
              id: Base
              type: object
              required:
                - name
                - size
                - author
                - license
                - contentType
                - contentUrls
                - price
                - type
              properties:
                name:
                  type: string
                  description: Descriptive name of the Asset
                  example: UK Weather information 2011
                description:
                  type: string
                  description: Details of what the resource is. For a data set explain what the data represents and what it can be used for.
                  example: Weather information of UK including temperature and humidity
                size:
                  type: string
                  description: Size of the asset. In the absence of a unit (mb, kb etc.), KB will be assumed
                  example: 3.1gb
                author:
                  type: string
                  description: Name of the entity generating this data.
                  example: Met Office
                license:
                  type: string
                  description: Short name referencing to the license of the asset (e.g. Public Domain, CC-0, CC-BY, No License Specified, etc. ). If it's not specified "No License Specifiedified" by default.
                  example: CC-BY
                copyrightHolder:
                  type: string
                  description: The party holding the legal copyright. Empty by default
                  example: Met Office
                encoding:
                  type: string
                  description: File encoding
                  example: UTF-8
                compression:
                  type: string
                  description: File compression
                  example: zip
                contentType:
                  type: string
                  description: File format if applicable
                  example: text/csv
                workExample:
                  type: string
                  description: Example of the concept of this asset. This example is part of the metadata, not an external link.
                  example: stationId,latitude,longitude,datetime,temperature,humidity\n
                      423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68
                contentUrls:
                  type: array
                  description: List of content urls resolving the ASSET files
                  example: ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"]
                links:
                  type: array
                  description: Mapping of links for data samples, or links to find out more information. The key represents the topic of the link, the value is the proper link
                  example: [{"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                            {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                            {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}]
                inLanguage:
                  type: string
                  description: The language of the content or performance or used in an action. Please use one of the language codes from the IETF BCP 47 standard.
                  example: en
                tags:
                  type: string
                  description: Keywords or tags used to describe this content. Multiple entries in a keywords list are typically delimited by commas. Empty by default
                  example: weather, uk, 2011, temperature, humidity
                price:
                  type: number
                  description: Price of the asset.
                  example: 10
                type:
                  type: string
                  description: Type of the Asset. Helps to filter by kind of asset, initially ("dataset", "algorithm", "container", "workflow", "other")
                  example: dataset
            curation:
              id: Curation
              type: object
              properties:
                rating:
                  type: number
                  description: Decimal values between 0 and 1. 0 is the default value
                  example: 0
                numVotes:
                  type: integer
                  description: any additional information worthy of highlighting (description maybe sufficient)
                  example: 0
                schema:
                  type: string
                  description: Schema applied to calculate the rating
                  example: Binary Votting
            additionalInformation:
              id: additionalInformation
              type: object
              properties:
                updateFrecuency:
                  type: string
                  description: ow often are updates expected
                  example: yearly
    responses:
      201:
        description: Asset successfully registered.
      400:
        description: One of the required attributes is missed.
      404:
        description: Invalid asset data.
      500:
        description: Error
    """
    assert isinstance(request.json, dict), 'invalid payload format.'
    required_attributes = ['assetId', 'publisherId', 'base']
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls', 'type']
    data = request.json
    if not data:
        logging.error('request body seems empty, expecting %s' % str(required_attributes))
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            logging.error('%s is required, got %s' % (attr, str(data)))
            return '"%s" is required for registering an asset.' % attr, 400

    for attr in required_metadata_base_attributes:
        if attr not in data['base']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['base'])))
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record = data
    _record['base']['dateCreated'] = datetime.utcnow().replace(microsecond=0).replace(
        tzinfo=pytz.UTC).isoformat()
    _record['curation']['rating'] = 0.00
    _record['curation']['numVotes'] = 0
    _record['additionalInformation']['checksum'] = hashlib.sha3_256(
        json.dumps(data['base']).encode('UTF-8')).hexdigest()
    # _record['publisherId'] = data['publisherId']
    # _record['assetId'] = data['assetId']
    try:
        dao.register(_record, data['assetId'])
        # add new assetId to response
        return _sanitize_record(_record), 201
    except Exception as err:
        logging.error('encounterd an error while saving the asset data to oceandb: {}'.format(str(err)))
        return 'Some error: "%s"' % str(err), 500


@assets.route('/metadata/<asset_id>', methods=['PUT'])
def update(asset_id):
    """Update metadata of an asset
    ---
    tags:
      - assets
    consumes:
      - application/json
    parameters:
      - name: asset_id
        in: path
        description: ID of the asset.
        required: true
        type: string
      - in: body
        name: body
        required: true
        description: Asset metadata.
        schema:
          type: object
          required:
            - asset_id
            - publisherId
            - base
          properties:
            publisherId:
              description: Id of the asset's publisher.
              type: string
              example: '0x0234242345'
            base:
              id: BaseUpdate
              type: object
              required:
                - name
                - size
                - author
                - license
                - contentType
                - contentUrls
                - price
                - type
              properties:
                name:
                  type: string
                  description: Descriptive name of the Asset
                  example: UK Weather information 2011
                description:
                  type: string
                  description: Details of what the resource is. For a data set explain what the data represents and what it can be used for.
                  example: Weather information of UK including temperature and humidity
                size:
                  type: string
                  description: Size of the asset. In the absence of a unit (mb, kb etc.), KB will be assumed
                  example: 3.1gb
                author:
                  type: string
                  description: Name of the entity generating this data.
                  example: Met Office
                license:
                  type: string
                  description: Short name referencing to the license of the asset (e.g. Public Domain, CC-0, CC-BY, No License Specified, etc. ). If it's not specified "No License Specifiedified" by default.
                  example: CC-BY
                copyrightHolder:
                  type: string
                  description: The party holding the legal copyright. Empty by default
                  example: Met Office
                encoding:
                  type: string
                  description: File encoding
                  example: UTF-8
                compression:
                  type: string
                  description: File compression
                  example: zip
                contentType:
                  type: string
                  description: File format if applicable
                  example: text/csv
                workExample:
                  type: string
                  description: Example of the concept of this asset. This example is part of the metadata, not an external link.
                  example: stationId,latitude,longitude,datetime,temperature,humidity\n
                      423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68
                contentUrls:
                  type: array
                  description: List of content urls resolving the ASSET files
                  example: ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"]
                links:
                  type: array
                  description: Mapping of links for data samples, or links to find out more information. The key represents the topic of the link, the value is the proper link
                  example: [{"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                            {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                            {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}]
                inLanguage:
                  type: string
                  description: The language of the content or performance or used in an action. Please use one of the language codes from the IETF BCP 47 standard.
                  example: en
                tags:
                  type: string
                  description: Keywords or tags used to describe this content. Multiple entries in a keywords list are typically delimited by commas. Empty by default
                  example: weather, uk, 2011, temperature, humidity
                price:
                  type: number
                  description: Price of the asset.
                  example: 10
                type:
                  type: string
                  description: Type of the Asset. Helps to filter by kind of asset, initially ("dataset", "algorithm", "container", "workflow", "other")
                  example: dataset
            curation:
              id: CurationUpdate
              type: object
              required:
                - rating
                - numVotes
              properties:
                rating:
                  type: number
                  description: Decimal values between 0 and 1. 0 is the default value
                  example: 0
                numVotes:
                  type: integer
                  description: any additional information worthy of highlighting (description maybe sufficient)
                  example: 0
                schema:
                  type: string
                  description: Schema applied to calculate the rating
                  example: Binary Votting
            additionalInformation:
              id: additionalInformationUpdate
              type: object
              properties:
                updateFrecuency:
                  type: string
                  description: ow often are updates expected
                  example: yearly
    responses:
      200:
        description: Asset successfully updated.
      400:
        description: One of the required attributes is missed.
      404:
        description: Invalid asset data.
      500:
        description: Error
    """
    required_attributes = ['base', 'publisherId', ]
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls', 'type']
    required_metadata_curation_attributes = ['rating', 'numVotes']

    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            return '"%s" is required for registering an asset.' % attr, 400

    for attr in required_metadata_base_attributes:
        if attr not in data['base']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['base'])))
            return '"%s" is required for registering an asset.' % attr, 400

    for attr in required_metadata_curation_attributes:
        if attr not in data['curation']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['curation'])))
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    date_created = dao.get(asset_id)['base']['dateCreated']
    _record = dict()
    _record = data
    _record['base']['dateCreated'] = date_created
    _record['additionalInformation']['checksum'] = hashlib.sha3_256(
        json.dumps(data['base']).encode('UTF-8')).hexdigest()
    _record['assetId'] = asset_id
    try:
        dao.update(_record, asset_id)
        return _sanitize_record(_record), 200
    except Exception as err:
        return 'Some error: "%s"' % str(err), 500


@assets.route('/metadata/<asset_id>', methods=['DELETE'])
def retire(asset_id):
    """Retire metadata of an asset
    ---
    tags:
      - assets
    parameters:
      - name: asset_id
        in: path
        description: ID of the asset.
        required: true
        type: string
    responses:
      200:
        description: successfully deleted
      404:
        description: This asset id is not in OceanDB
      500:
        description: Error
    """
    try:
        if dao.get(asset_id) is None:
            return 'This asset id is not in OceanDB', 404
        else:
            dao.delete(asset_id)
            return 'Succesfully deleted', 200
    except Exception as err:
        return 'Some error: "%s"' % str(err), 500


@assets.route('/metadata', methods=['GET'])
def get_assets_metadata():
    """Get metadata of all assets.
    ---
    tags:
      - assets
    responses:
      200:
        description: successful action
    """
    args = []
    query = dict()
    args.append(query)
    assets_with_id = dao.get_assets()
    assets_metadata = {a['assetId']: a for a in assets_with_id}
    return jsonify(json.dumps(assets_metadata)), 200


@assets.route('/metadata/query', methods=['POST'])
def query_metadata():
    """Get a list of assets that match with the query executed.
    ---
    tags:
      - assets
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
            text:
              type: string
              description: Word to search in the document
              example: Office
            sort:
              type: object
              description: key or list of keys to sort the result
              example: {"value":1}
            offset:
              type: int
              description:
              example: 100
            page:
              type: int
              description:
              example: 0
    responses:
      200:
        description: successful action
    """
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'
    if 'query' in data:
        search_model = QueryModel(query=data.get('query'), sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 0))
    elif 'text' in data:
        search_model = FullTextModel(text=data.get('text'), sort=data.get('sort'),
                                     offset=data.get('offset', 100),
                                     page=data.get('page', 0))
    else:
        search_model = QueryModel(query={}, sort=data.get('sort'),
                                  offset=data.get('offset', 100),
                                  page=data.get('page', 0))
    query_result = dao.query(search_model)
    for i in query_result:
        _sanitize_record(i)
    return jsonify(json.dumps(query_result)), 200


@assets.route('/metadata/consume/<asset_id>', methods=['POST'])
def consume_resource(asset_id):
    """Allows download of asset data file from this provider.

    Data file can be stored locally at the provider end or at some cloud storage.
    It is assumed that the asset is already purchased by the consumer (even for
    free/commons assets, the consumer must still go through the purchase contract
    transaction).

    ---
    tags:
      - assets

    consumes:
      - application/json
    parameters:
      - name: asset_id
        in: path
        description: ID of the asset.
        required: true
        type: string
      - in: body
        name: body
        required: true
        description: Asset metadata.
        schema:
          type: object
          required:
            - challenge_id
          properties:
            challenge_id:
              description:
              type: string
              example: '0x0234242345'

    """
    # Get asset metadata record
    required_attributes = ['consumerId', 'fixed_msg', 'sigEncJWT', 'jwt']
    assert isinstance(request.json, dict), 'invalid payload format.'
    logging.info('got "consume" request: %s' % request.json)
    data = request.json
    if not data:
        logging.error('Consume failed: data is empty.')
        return 'payload seems empty.', 400

    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            logging.error('Consume failed: required attr %s missing.' % attr)
            return '"%s" is required for registering an asset.' % attr, 400

    contract_instance = ocn.contracts.auth.contract_concise
    sig = ocn.helper.split_signature(ocn.web3.toBytes(hexstr=data['sigEncJWT']))
    jwt = decode(data['jwt'])

    if contract_instance.verifyAccessTokenDelivery(jwt['request_id'],  # requestId
                                                   ocn.web3.toChecksumAddress(data['consumerId']),
                                                   # consumerId
                                                   data['fixed_msg'],
                                                   sig.v,  # sig.v
                                                   sig.r,  # sig.r
                                                   sig.s,  # sig.s
                                                   transact={'from': ocn.web3.eth.accounts[0] if config.get(
                                                       ConfigSections.KEEPER_CONTRACTS, 'provider.account') is '' else config.get(
                                                       ConfigSections.KEEPER_CONTRACTS, 'provider.account'),
                                                             'gas': 4000000}):
        if jwt['resource_server_plugin'] == 'Azure':
            logging.info('reading asset from oceandb: %s' % asset_id)
            urls = dao.get(asset_id)['base']['contentUrls']
            url_list = []
            for url in urls:
                url_list.append(generate_sasurl(url, config.get(ConfigSections.RESOURCES, 'azure.account.name'),
                                                config.get(ConfigSections.RESOURCES, 'azure.account.key'),
                                                config.get(ConfigSections.RESOURCES, 'azure.container')))
            return jsonify(url_list), 200
        else:
            logging.error('resource server plugin is not supported: %s' % jwt['resource_server_plugin'])
            return '"%s error generating the sasurl.' % asset_id, 404
    else:
        return '"%s error generating the sasurl.' % asset_id, 404


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)


def validate_asset_data(data):
    return ''
