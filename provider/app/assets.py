import pytz
import json
import logging
import hashlib
from datetime import datetime
from flask import Blueprint, jsonify, request
from provider.app.osmosis import generate_sasurl
from ocean_web3.constants import OceanContracts
from provider.myapp import app
from ocean_web3.acl import decode
from ocean_web3.ocean_contracts import OceanContractsWrapper
from ocean_web3.config_parser import load_config_section
from provider.constants import ConfigSections, BaseURLs
from provider.app.dao import Dao
from provider.app.filters import Filters
from provider.log import setup_logging


setup_logging()
assets = Blueprint('assets', __name__)

config_file = app.config['CONFIG_FILE']
# Prepare keeper contracts for on-chain access control
keeper_config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)
res_conf = load_config_section(config_file, ConfigSections.RESOURCES)
# Prepare OceanDB
dao = Dao(config_file)

provider_url = '%s://%s:%s' % (res_conf['provider.scheme'], res_conf['provider.host'], res_conf['provider.port'])
provider_url += BaseURLs.ASSETS_URL
provider_address = None if not keeper_config['provider.address'] else keeper_config['provider.address']
ocean_contracts = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'],
                                        provider_address)

ocean_contracts.init_contracts()
# Prepare resources access configuration to download assets
resources_config = load_config_section(config_file, ConfigSections.RESOURCES)


def get_provider_address_filter():
    account = ocean_contracts.web3.eth.accounts[0] if not keeper_config['provider.address'] \
        else keeper_config['provider.address']
    return {"address": account}


ocn_for_filters = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'],
                                        provider_address)
ocn_for_filters.init_contracts()

filters = Filters(ocean_contracts_wrapper=ocn_for_filters, config_file=config_file, api_url=provider_url)
filter_access_consent = ocn_for_filters.watch_event(OceanContracts.OACL,
                                                    'AccessConsentRequested',
                                                    filters.commit_access_request,
                                                    0.2,
                                                    fromBlock='latest',
                                                    filters=get_provider_address_filter())

filter_payment = ocn_for_filters.watch_event(OceanContracts.OMKT,
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
            - metadata
          properties:
            assetId:
              description: ID of the asset.
              example: '0x1298371984723941'
              type: string
            publisherId:
              description: Id of the asset's publisher.
              type: string
              example: '0x0234242345'
            metadata:
              schema:
                id: Metadata
                type: object
                required:
                  - base
                properties:
                  base:
                    id: Base
                    type: object
                    required:
                      - name
                      - dateCreated
                      - size
                      - author
                      - license
                      - contentType
                      - contentUrls
                      - price
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
    required_attributes = ['assetId', 'metadata', 'publisherId', ]
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls']
    data = request.json
    if not data:
        logging.error('request body seems empty, expecting %s' % str(required_attributes))
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            logging.error('%s is required, got %s' % (attr, str(data)))
            return '"%s" is required for registering an asset.' % attr, 400

    if not data['metadata']['base']:
        logging.error('metadata base is required')
        return 'metadata base is required for registering an asset.', 400
    for attr in required_metadata_base_attributes:
        if attr not in data['metadata']['base']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['metadata']['base'])))
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record['metadata'] = data['metadata']
    _record['metadata']['base']['dateCreated'] = datetime.utcnow().replace(microsecond=0).replace(tzinfo=pytz.UTC).isoformat()
    _record['metadata']['curation']['rating'] = 0.00
    _record['metadata']['curation']['numVotes'] = 0
    _record['metadata']['additionalInformation']['checksum'] = hashlib.sha3_256(
        json.dumps(data['metadata']['base']).encode('UTF-8')).hexdigest()
    _record['publisherId'] = data['publisherId']
    _record['assetId'] = data['assetId']
    try:
        # dao.register(_record)
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
            - metadata
          properties:
            publisherId:
              description: Id of the asset's publisher.
              type: string
              example: '0x0234242345'
            metadata:
              schema:
                id: MetadataUpdate
                type: object
                required:
                  - base
                properties:
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
    required_attributes = ['metadata', 'publisherId', ]
    required_metadata_base_attributes = ['name', 'size', 'author', 'license', 'contentType',
                                         'contentUrls']
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
        if attr not in data['metadata']['base']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['metadata']['base'])))
            return '"%s" is required for registering an asset.' % attr, 400

    for attr in required_metadata_curation_attributes:
        if attr not in data['metadata']['curation']:
            logging.error('%s metadata is required, got %s' % (attr, str(data['metadata']['curation'])))
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    date_created = dao.get(asset_id)['metadata']['base']['dateCreated']
    _record = dict()
    _record['metadata'] = data['metadata']
    _record['metadata']['base']['dateCreated'] = date_created
    _record['metadata']['additionalInformation']['checksum'] = hashlib.sha3_256(
        json.dumps(data['metadata']['base']).encode('UTF-8')).hexdigest()
    _record['publisherId'] = data['publisherId']
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
        dao.delete(asset_id)
        return '', 200
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

    contract_instance = ocean_contracts.contracts[OceanContracts.OCEAN_ACL_CONTRACT][0]
    sig = ocean_contracts.split_signature(ocean_contracts.web3.toBytes(hexstr=data['sigEncJWT']))
    jwt = decode(data['jwt'])

    if contract_instance.verifyAccessTokenDelivery(jwt['request_id'],  # requestId
                                                   ocean_contracts.web3.toChecksumAddress(data['consumerId']),
                                                   # consumerId
                                                   data['fixed_msg'],
                                                   sig.v,  # sig.v
                                                   sig.r,  # sig.r
                                                   sig.s,  # sig.s
                                                   transact={'from': ocean_contracts.account,
                                                             'gas': 4000000}):
        if jwt['resource_server_plugin'] == 'Azure':
            logging.info('reading asset from oceandb: %s' % asset_id)
            urls = dao.get(asset_id)['metadata']['base']['contentUrls']
            url_list = []
            for url in urls:
                url_list.append(generate_sasurl(url, resources_config['azure.account.name'],
                                                resources_config['azure.account.key'],
                                                resources_config['azure.container']))
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
