import os, json, datetime

from flask import Blueprint, jsonify, request
from oceandb_driver_interface import OceanDb
from azure.storage.blob import BlobService
from azure.storage import AccessPolicy, SharedAccessPolicy

from provider_backend.blockchain.constants import OceanContracts
from provider_backend.myapp import app
from werkzeug.utils import secure_filename
import json

from provider_backend.blockchain.OceanContractsWrapper import OceanContractsWrapper
from provider_backend.config_parser import load_config_section
from provider_backend.constants import ConfigSections
from provider_backend.app.dao import Dao

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'osx', 'doc'}

assets = Blueprint('assets', __name__)

config_file = app.config['CONFIG_FILE']
# Prepare OceanDB
dao= Dao(config_file)

# Prepare keeper contracts for on-chain access control
keeper_config = load_config_section(config_file, ConfigSections.KEEPER_CONTRACTS)
ocean_contracts = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'])
ocean_contracts.init_contracts()
# Prepare resources access configuration to download assets
recources_config = load_config_section(config_file, ConfigSections.RESOURCES)
# ocean_contracts = OceanContractsWrapper(keeper_config['keeper.host'], keeper_config['keeper.port'])

ASSETS_FOLDER = app.config['UPLOADS_FOLDER']


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
    # assets = oceandb.list()
    # asset_with_id = []
    # for asset in assets:
    #     try:
    #         asset_with_id.append(oceandb.read(asset['id']))
    #     except:
    #         pass
    asset_with_id=dao.get_assets()

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
        # tx_id = find_tx_id(asset_id)
        # asset_record = oceandb.read(tx_id)
        asset_record = dao.get(asset_id)
        return jsonify(asset_record['data']), 200
    except Exception as e:
        return '"%s asset_id is not in OceanDB' % asset_id, 404




# def find_tx_id(asset_id):
#     all = oceandb.list()
#     for a in all:
#         if a['data']['data']['assetId'] == asset_id:
#             return a['id']
#         else:
#             pass
#     return "%s not found" % asset_id


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
        # oceandb.write(_record)
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
        # tx_id = find_tx_id(asset_id)
        # oceandb.update(_record, tx_id)
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
        # tx_id = find_tx_id(asset_id)
        # oceandb.delete(tx_id)
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
    # assets = oceandb.list()
    # assets_with_id = []
    # for asset in assets:
    #     try:
    #         assets_with_id.append((oceandb.read(asset['id'])))
    #     except Exception as e:
    #         return 'Some error: "%s"' % str(e), 500
    assets_with_id=dao.get_assets()
    assets_metadata = {a['data']['data']['assetId']: a['data']['data'] for a in assets_with_id}
    return jsonify(json.dumps(assets_metadata)), 200


@assets.route('/consume/<asset_id>', methods=['GET'])
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
    # Validate accessToken
    # grab encrypted accessToken from blockchain for this assetId and consumerId
    # encrypt accessToken with consumer public key then compare with the fetched token from chain
    # Verify consumer has permission to consume this asset (on-chain authorization)

    # Get asset metadata record
    required_attributes = ['accessId', 'consumerId', 'fixed_msg', 'sigEncJWT']
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            return '"%s" is required for registering an asset.' % attr, 400

    contract_instance = ocean_contracts.contracts[OceanContracts.OCEAN_ACL_CONTRACT][0]
    sig = OceanContractsWrapper.split_signature(data['sigEncJWT'])

    if contract_instance.verifyAccessTokenDelivery(data['accessId'],  # accessId
                                                   data['consumerId'],  # consumerId
                                                   ocean_contracts.web3.toHex(data['fixed_msg']), #Depend of the request to hex
                                                   sig.v,  # sig.v
                                                   sig.r,  # sig.r
                                                   sig.s,  # sig.s
                                                   transact={'from': keeper_config['provider.address']}):
        # url = oceandb.read(asset_id)['metadata']['links']
        url = dao.get(asset_id)['metadata']['links']
        return generate_sasurl(url), 200


@assets.route('/asset/{asset_id}', methods=['POST'])
def upload_data(asset_id, body=None, publisher_id=None):
    """

    :param asset_id: a str identifying an asset in the ocean network
    :param publisher_id: the ethereum address of the owner of this asset
    :return:
    """
    reques = request
    # TODO
    # update asset metadata to specify that this asset is available for download from this provider directly.

    # require parameter
    # if not publisher_id:
    #     return "This call requires some arguments but none were provided. Publisher id is required", 401
    #
    # # verify that this asset exists and not disabled
    # resource_record = oceandb.read(asset_id)
    # if not resource_record:
    #     return "Data asset '%s' not found." % asset_id, 404
    #
    # # verify that the publisher is the same that published the asset
    # if publisher_id != resource_record['publisherId']:
    #     return "Actor %s not authorized to upload in this asset." % publisher_id, 401
    #
    # file_path = None
    # try:
    #     if not isinstance(body, dict) or 'file' not in body or not body['file']:
    #         return "Malformed file upload request.", 400
    #
    #     file_value = body['file']
    #     assert len(file_value) == 2
    #     file_name = body['file'][0]
    #     input_file = body['file'][1]
    #     if not allowed_file(file_name):
    #         return 400
    #
    #     # file_type = body.get('filetype')
    #     # if file_type is not None:
    #     #     assets_db.update_one({'assetId': asset_id}, {'$set': {'contentType': file_type}})
    #
    #     asset_folder = os.path.join(ASSETS_FOLDER, asset_id)
    #     if not os.path.exists(asset_folder):
    #         os.makedirs(asset_folder)
    #
    #     file_name = secure_filename(file_name)
    #     file_path = os.path.join(asset_folder, file_name) + '~'
    #     if os.path.exists(file_path[:-1]):
    #         return "Resource already exists with the same name. Try uploading using a different file name.", 422
    #
    #     if os.path.exists(file_path):
    #         os.remove(file_path)
    #
    #     with open(file_path, 'wb') as output_file:
    #         _size = 4096
    #         while True:
    #             chunk = input_file.read(_size)
    #             if not chunk:
    #                 break
    #             output_file.write(chunk)
    #
    #     os.rename(file_path, file_path[:-1])
    #
    #     return 'File saved successfully to "%s"' % file_path[:-1], 201
    #
    # except Exception as err:
    #     print('Error: "%s"' % str(err))
    #     if file_path and os.path.exists(file_path):
    #         os.remove(file_path)
    #     return str(err), 500


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)


def validate_asset_data(data):
    return ''


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_sasurl(url):
    bs = BlobService(account_name=recources_config['azure.account.name'],
                     account_key=recources_config['azure.account.key'])
    today = datetime.datetime.utcnow()
    todayPlusMonth = today + datetime.timedelta(30)
    todayPlusMonthISO = todayPlusMonth.replace(microsecond=0).isoformat() + 'Z'
    sasToken = bs.generate_shared_access_signature(recources_config['azure.container'], None, SharedAccessPolicy(
        AccessPolicy(None, todayPlusMonthISO, "rw"), None))
    return url + "?" + sasToken
