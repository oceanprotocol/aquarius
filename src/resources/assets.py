import os

import hug
import falcon
from werkzeug.utils import secure_filename

from ConfigOptions import ConfigOptions
from constants import DEFAULT_ASSETS_FOLDER
from database.instance import sanitize_record, get_oceandb_instance
from resources.resource_base import ResourceBase
from resources.resource_constants import AssetStates, AssetTypes


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'osx', 'doc'}


def allowed_file(filename):
    return True  # '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@hug.object.urls()
class AssetsResource(ResourceBase):
    URL_PREFIX = ''
    RESOURCE_URL = '/assets'

    def __init__(self):
        ResourceBase.__init__(self)

        self.assets_folder = DEFAULT_ASSETS_FOLDER
        assets_folder = ConfigOptions().getValue('assets-folder')
        if assets_folder and os.path.exists(assets_folder):
            self.assets_folder = assets_folder

    @hug.object.get('/metadata/{asset_id}')
    def get(self, response, asset_id):
        db_instance = get_oceandb_instance().instance
        asset_record = db_instance.read(asset_id)
        return asset_record['data']

    @hug.object.get('/')
    def get_assets(self, response):
        args = []
        query = dict()

        args.append(query)

        db_instance = get_oceandb_instance().instance
        assets = db_instance.query(AssetTypes.DATA_ASSET)
        asset_ids = [a['id'] for a in assets]
        response.status = falcon.HTTP_200
        resp_body = dict({'assetsIds': asset_ids})

        return resp_body

    @hug.object.get('/metadata')
    def get_assets_metadata(self, response):
        args = []
        query = dict()

        args.append(query)

        db_instance = get_oceandb_instance().instance
        assets = db_instance.query(AssetTypes.DATA_ASSET)
        assets_metadata = {a['id']: a['data'] for a in assets}
        response.status = falcon.HTTP_200

        return assets_metadata

    @hug.object.put('/{asset_id}')
    def update(self, request, response, body, asset_id):
        # TODO:
        pass

    @hug.object.post('/')
    def register(self, request, response, body):
        required_attributes = ['title', 'publisherId', ]
        db_instance = get_oceandb_instance().instance
        assert isinstance(body, dict), 'invalid payload format.'

        data = body
        if not data:
            response.status = falcon.HTTP_400
            return
        assert isinstance(data, dict), 'invalid `body` type, should already formatted into a dict.'

        for attr in required_attributes:
            if attr not in data:
                response.status = falcon.HTTP_400
                return '"%s" is required for registering an asset.' % attr

        msg = self.validate_asset_data(data)
        if msg:
            response.status = falcon.HTTP_404
            return msg

        _record = dict()
        _record['data'] = data
        _record['assetType'] = AssetTypes.DATA_ASSET
        try:
            tx = db_instance.write(_record)
            response.status = falcon.HTTP_201
            # add new assetId to response
            _record['assetId'] = tx['id']
            return sanitize_record(_record)
        except Exception as err:
            response.status = falcon.HTTP_500
            return 'Some error: "%s"' % str(err)

    @hug.object.get('/download/{asset_id}', output=hug.output_format.file)
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
        db = get_oceandb_instance().instance
        asset_record = db.read(asset_id)
        if not asset_record:
            response.status = falcon.HTTP_404
            return 'This asset id cannot be found. Please verify this asset id is correct.'

        asset_folder_path = os.path.join(self.assets_folder, asset_id)
        if not os.path.exists(asset_folder_path) or not os.listdir(asset_folder_path):
            response.status = falcon.HTTP_404
            return 'The requested dataset was not found. Ask the provider/publisher to upload the dataset.'

        files = []
        for filename in os.listdir(asset_folder_path):
            file_path = os.path.join(asset_folder_path, filename)
            files.append(file_path)

        if not files:
            response.status = falcon.HTTPNotFound
            return 'Resource not found.'

        response.status = falcon.HTTP_200
        content_type = asset_record.get("contentType")
        if content_type:
            response.set_header("content-type", content_type)

        # check asset metadata to figure out whether asset is stored locally or stored on the cloud

        return files[0]

    @hug.object.post('/upload/{asset_id}')
    def upload_data(self, body, response, asset_id, publisher_id=None):
        """

        :param asset_id: a str identifying an asset in the ocean network
        :param publisher_id: the ethereum address of the owner of this asset
        :return:
        """

        # TODO
        # update asset metadata to specify that this asset is available for download from this provider directly.

        db = get_oceandb_instance().instance
        # require parameter
        if not publisher_id:
            response.status = falcon.HTTP_UNAUTHORIZED
            return "This call requires some arguments but none were provided. Publisher id is required"

        # verify that this asset exists and not disabled
        resource_record = db.read(asset_id)
        if not resource_record:
            response.status = falcon.HTTP_404
            return "%s not found." % self._resource_label

        # verify that the publisher is the same that published the asset
        if publisher_id != resource_record['publisherId']:
            response.status = falcon.HTTP_UNAUTHORIZED
            return "Actor %s not authorized to upload in this asset." % publisher_id

        file_path = None
        try:
            if not isinstance(body, dict) or 'file' not in body or not body['file']:
                response.status = falcon.HTTP_400
                return "Malformed file upload request."

            file_value = body['file']
            assert len(file_value) == 2
            file_name = body['file'][0]
            input_file = body['file'][1]
            if not allowed_file(file_name):
                response.status = 'File name is not valid.'
                return falcon.HTTP_BAD_REQUEST

            # file_type = body.get('filetype')
            # if file_type is not None:
            #     assets_db.update_one({'assetId': asset_id}, {'$set': {'contentType': file_type}})

            asset_folder = os.path.join(self.assets_folder, asset_id)
            if not os.path.exists(asset_folder):
                os.makedirs(asset_folder)

            file_name = secure_filename(file_name)
            file_path = os.path.join(asset_folder, file_name) + '~'
            if os.path.exists(file_path[:-1]):
                response.status = falcon.HTTP_UNPROCESSABLE_ENTITY
                return "Resource already exists with the same name. Try uploading using a different file name."

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
            response.status = falcon.HTTP_201

            return 'File saved successfully to "%s"' % file_path[:-1]

        except Exception as err:
            print('Error: "%s"' % str(err))
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            response.status = falcon.HTTP_500
            return str(err)

    def validate_asset_data(self, data):
        return ''
