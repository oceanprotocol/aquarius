from flask import Blueprint, jsonify, request
from provider.app.osmosis import generate_sasurl
from blockchain.constants import OceanContracts
from provider.myapp import app
import json
from acl.acl import decode
from blockchain.OceanContractsWrapper import OceanContractsWrapper
from provider.config_parser import load_config_section
from provider.constants import ConfigSections, BaseURLs
from provider.app.dao import Dao
from provider.app.filters import Filters

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'osx', 'doc'}
assets = Blueprint('assets', __name__)

config_file = app.config['CONFIG_FILE']
# Prepare OceanDB
dao = Dao(config_file)
# Prepare keeper contracts for on-chain access control
keeper_config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)
res_conf = load_config_section(config_file, ConfigSections.RESOURCES)
provider_url = '%s://%s:%s' % (res_conf['provider.scheme'], res_conf['provider.host'], res_conf['provider.port'])
provider_url += BaseURLs.ASSETS_URL
provider_address = None if not keeper_config['provider.address'] else keeper_config['provider.address']
ocean_contracts = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'],
                                        provider_address)

ocean_contracts.init_contracts()
# Prepare resources access configuration to download assets
resources_config = load_config_section(config_file, ConfigSections.RESOURCES)

ASSETS_FOLDER = app.config['UPLOADS_FOLDER']


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

    asset_ids = [a['data']['data']['assetId'] for a in asset_with_id]
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
        return jsonify(asset_record['data']), 200
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
                  - name
                  - links
                  - size
                  - format
                  - description
                properties:
                  name:
                    type: string
                    description: a few words describing the resource.
                    example: Berling Climate NetCDF
                  links:
                    type: array
                    description: links for data samples, or links to find out more information
                    example: ["https://www.beringclimate.noaa.gov/cache/5b322cddd36bc.zip","https://www.beringclimate.noaa.gov/cache/5b322cddd36bc.zip"]
                  size:
                    type: string
                    description: size of data in MB, GB, or Tera bytes
                    example: 0.000217GB
                  format:
                    type: string
                    description: file format if applicable
                    example: .zip
                  description:
                    type: string
                    description: details of what the resource is. For a data set explain what the data represents and what it can be used for.
                    example: Climate indices, atmosphere, ocean, fishery, biology, and sea ice data files.
                  date:
                    type: string
                    description: date the resource was made available
                    example: 01-01-2019
                  labels:
                    type: array
                    description: labels can serve the role of multiple categories
                    example: [climate, ocean, atmosphere, temperature]
                  license:
                    type: string
                    example: propietary
                  classification:
                    type: string
                    example: public
                  industry:
                    type: string
                    example: Earth Sciences
                  category:
                    type: string
                    description: can be assigned to a category in addition to having labels
                    example: Climate
                  note:
                    type: string
                    description: any additional information worthy of highlighting (description maybe sufficient)
                  keywords:
                    type: array
                    description: can enhance search and find functions
                    example: [climate, ocean, atmosphere, temperature]
                  updateFrequency:
                    type: string
                    description: how often are updates expected (seldome, annual, quarterly, etc.), or is the resource static (never expected to get updated)
                    example: static
                  lifecycleStage:
                    type: string
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
    required_metadata_attributes = ['name', 'links', 'size', 'format', 'description']

    data = request.json
    if not data:
        print('request body seems empty, expecting %s' % str(required_attributes))
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            print('%s is required, got %s' % (attr, str(data)))
            return '"%s" is required for registering an asset.' % attr, 400

    for attr in required_metadata_attributes:
        if attr not in data['metadata']:
            print('%s metadata is required, got %s' % (attr, str(data['metadata'])))
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record['metadata'] = data['metadata']
    _record['publisherId'] = data['publisherId']
    _record['assetId'] = data['assetId']
    try:
        dao.register(_record)
        # add new assetId to response
        return _sanitize_record(_record), 201
    except Exception as err:
        print('encounterd an error while saving the asset data to oceandb: %s' % str(err))
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
            - publisherId
            - metadata
          properties:
            publisherId:
              description: Id of the asset's publisher.
              type: string
              example: '0x0234242345'
            metadata:
              schema:
                id: Metadata
                type: object
                required:
                  - name
                  - links
                  - size
                  - format
                  - description
                properties:
                  name:
                    type: string
                    description: a few words describing the resource.
                    example: Berling Climate NetCDF
                  links:
                    type: array
                    description: links for data samples, or links to find out more information
                    example: ["https://www.beringclimate.noaa.gov/cache/5b322cddd36bc.zip","https://www.beringclimate.noaa.gov/cache/5b322cddd36bc.zip"]
                  size:
                    type: string
                    description: size of data in MB, GB, or Tera bytes
                    example: 0.000217GB
                  format:
                    type: string
                    description: file format if applicable
                    example: .zip
                  description:
                    type: string
                    description: details of what the resource is. For a data set explain what the data represents and what it can be used for.
                    example: Climate indices, atmosphere, ocean, fishery, biology, and sea ice data files.
                  date:
                    type: string
                    description: date the resource was made available
                    example: 01-01-2019
                  labels:
                    type: array
                    description: labels can serve the role of multiple categories
                    example: [climate, ocean, atmosphere, temperature]
                  license:
                    type: string
                    example: propietary
                  classification:
                    type: string
                    example: public
                  industry:
                    type: string
                    example: Earth Sciences
                  category:
                    type: string
                    description: can be assigned to a category in addition to having labels
                    example: Climate
                  note:
                    type: string
                    description: any additional information worthy of highlighting (description maybe sufficient)
                  keywords:
                    type: array
                    description: can enhance search and find functions
                    example: [climate, ocean, atmosphere, temperature]
                  updateFrequency:
                    type: string
                    description: how often are updates expected (seldome, annual, quarterly, etc.), or is the resource static (never expected to get updated)
                    example: static
                  lifecycleStage:
                    type: string
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
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            return '"%s" is required for registering an asset.' % attr, 400

    required_metadata_attributes = ['name', 'links', 'size', 'format', 'description']
    for attr in required_metadata_attributes:
        if attr not in data['metadata']:
            return '"%s" is required for registering an asset.' % attr, 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record['metadata'] = data['metadata']
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
        return 200
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
    assets_metadata = {a['data']['data']['assetId']: a['data']['data'] for a in assets_with_id}
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
    print('got "consume" request: ', request.json)
    data = request.json
    if not data:
        print('Consume failed: data is empty.')
        return 'payload seems empty.', 400

    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            print('Consume failed: required attr %s missing.' % attr)
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
            print('reading asset from oceandb: ', asset_id)
            url = dao.get(asset_id)['data']['data']['metadata']['links']
            sasurl = generate_sasurl(url, resources_config['azure.account.name'],
                                     resources_config['azure.account.key'],
                                     resources_config['azure.container'])
            return str(sasurl), 200
        else:
            print('resource server plugin is not supported: ', jwt['resource_server_plugin'])
            return '"%s error generating the sasurl.' % asset_id, 404
    else:
        return '"%s error generating the sasurl.' % asset_id, 404


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)


def validate_asset_data(data):
    return ''


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
