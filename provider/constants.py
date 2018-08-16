import os

DEFAULT_ASSETS_FOLDER = os.path.join(os.getcwd(), "asset_files")
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 5000


class ConfigSections:
    KEEPER_CONTRACTS = 'keeper-contracts'
    RESOURCES = 'resources'


class BaseURLs:
    BASE_PROVIDER_URL = '/api/v1/provider'
    SWAGGER_URL = '/api/v1/docs'  # URL for exposing Swagger UI (without trailing '/')
    API_URL = 'http://localhost:5000/spec'
    ASSETS_URL = BASE_PROVIDER_URL + '/assets'
