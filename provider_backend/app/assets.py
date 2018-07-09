from flask import Blueprint, jsonify, request
from oceandb_driver_interface import OceanDb
from provider_backend.app.resource_constants import AssetTypes
from werkzeug.utils import secure_filename
import json, os

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'osx', 'doc'}

assets = Blueprint('assets', __name__)
# metadata = Blueprint('metadata', __name__)
oceandb = OceanDb('oceandb.ini').plugin


# class AssetsResource(ResourceBase):
#     URL_PREFIX = ''
#     RESOURCE_URL = '/assets'
#
#     def __init__(self):
#         ResourceBase.__init__(self)
#         self.assets_folder = DEFAULT_ASSETS_FOLDER
        # assets_folder = ConfigOptions().getValue('assets-folder')
        # if assets_folder and os.path.exists(assets_folder):
        #     self.assets_folder = assets_folder

@assets.route('/hello', methods=['GET'])
def get_hello():
    return 'Hello'


#TODO create a different Blueprint
@assets.route('/metadata/<asset_id>', methods=['GET'])
def get(asset_id):
    asset_record = oceandb.read(asset_id)
    return jsonify(asset_record['data']), 200


@assets.route('/', methods=['GET'])
def get_assets():
    args = []
    query = dict()

    args.append(query)

    assets = oceandb.query(AssetTypes.DATA_ASSET)
    asset_ids = [a['id'] for a in assets]
    resp_body = dict({'assetsIds': asset_ids})

    return jsonify(resp_body), 200


@assets.route('/register', methods=['POST'])
def register():
    required_attributes = ['title', 'publisherId', ]
    assert isinstance(request.json, dict), 'invalid payload format.'
    data = request.json
    if not data:
        return 400
    assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

    for attr in required_attributes:
        if attr not in data:
            return '"%s" is required for registering an asset.' % attr , 400

    msg = validate_asset_data(data)
    if msg:
        return msg, 404

    _record = dict()
    _record['data'] = data
    _record['assetType'] = AssetTypes.DATA_ASSET
    try:
        tx = oceandb.write(_record)
        # add new assetId to response
        _record['assetId'] = tx['id']
        return _sanitize_record(_record), 201
    except Exception as err:
        return 'Some error: "%s"' % str(err), 500


@assets.route('/metadata', methods=['GET'])
def get_assets_metadata():
    args = []
    query = dict()
    args.append(query)
    assets = oceandb.query(AssetTypes.DATA_ASSET)
    assets_metadata = {a['id']: a['data'] for a in assets}

    return jsonify(assets_metadata), 200

@assets.route('/download/{asset_id}')
def download_data(self, response, asset_id, consumer_id, access_token):
    """Allows download of asset data file from this provider.

    Data file can be stored locally at the provider end or at some cloud storage.
    It is assumed that the asset is already purchased by the consumer (even for
    free/commons assets, the consumer must still go through the purchase contract
    transaction).

    Validation:
    - assetId is in the system and valid for this provider
    - consumerId is valid in the system and authorized to access this asset. This
    authorization is obtained from the on-chain contract by sending the assetId and
    consumerId.

    :param assetId: a str identifying an asset in the ocean network
    :param consumerId: the ethereum address of the user consuming this asset
    :param accessToken: a dict representing the access info/credentials of
        this asset specifically issued for this consumer
    :return:
        Serving the download request if everything validates ok
        Error/message if something fails the validation

    """
    # Validate accessToken
    # grab encrypted accessToken from blockchain for this assetId and consumerId
    # encrypt accessToken with consumer public key then compare with the fetched token from chain
    # Verify consumer has permission to consume this asset (on-chain authorization)

    # Get asset metadata record
    asset_record = oceandb.read(asset_id)
    if not asset_record:
        return 'This asset id cannot be found. Please verify this asset id is correct.', 404

    asset_folder_path = os.path.join(self.assets_folder, asset_id)
    if not os.path.exists(asset_folder_path) or not os.listdir(asset_folder_path):
        return 'The requested dataset was not found. Ask the provider/publisher to upload the dataset.', 404

    files = []
    for filename in os.listdir(asset_folder_path):
        file_path = os.path.join(asset_folder_path, filename)
        files.append(file_path)

    if not files:
        return 'Resource not found.', 404

    content_type = asset_record.get("contentType")
    if content_type:
        response.set_header("content-type", content_type)

    # check asset metadata to figure out whether asset is stored locally or stored on the cloud

    return files[0], 200

@assets.route('/upload/{asset_id}')
def upload_data(self, body, response, asset_id, publisher_id=None):
    """

    :param asset_id: a str identifying an asset in the ocean network
    :param publisher_id: the ethereum address of the owner of this asset
    :return:
    """

    # TODO
    # update asset metadata to specify that this asset is available for download from this provider directly.

    # require parameter
    if not publisher_id:
        return "This call requires some arguments but none were provided. Publisher id is required", 401

    # verify that this asset exists and not disabled
    resource_record = oceandb.read(asset_id)
    if not resource_record:
        return "%s not found." % self._resource_label, 404

    # verify that the publisher is the same that published the asset
    if publisher_id != resource_record['publisherId']:
        return "Actor %s not authorized to upload in this asset." % publisher_id, 401

    file_path = None
    try:
        if not isinstance(body, dict) or 'file' not in body or not body['file']:
            return "Malformed file upload request.", 400

        file_value = body['file']
        assert len(file_value) == 2
        file_name = body['file'][0]
        input_file = body['file'][1]
        if not allowed_file(file_name):
            return 400

        # file_type = body.get('filetype')
        # if file_type is not None:
        #     assets_db.update_one({'assetId': asset_id}, {'$set': {'contentType': file_type}})

        asset_folder = os.path.join(self.assets_folder, asset_id)
        if not os.path.exists(asset_folder):
            os.makedirs(asset_folder)

        file_name = secure_filename(file_name)
        file_path = os.path.join(asset_folder, file_name) + '~'
        if os.path.exists(file_path[:-1]):
            return "Resource already exists with the same name. Try uploading using a different file name.", 422

        if os.path.exists(file_path):
            os.remove(file_path)

        with open(file_path, 'wb') as output_file:
            _size = 4096
            while True:
                chunk = input_file.read(_size)
                if not chunk:
                    break
                output_file.write(chunk)

        os.rename(file_path, file_path[:-1])

        return 'File saved successfully to "%s"' % file_path[:-1], 201

    except Exception as err:
        print('Error: "%s"' % str(err))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return str(err), 500


def _sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)

def validate_asset_data(data):
    return ''

def allowed_file(filename):
    return True  # '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS