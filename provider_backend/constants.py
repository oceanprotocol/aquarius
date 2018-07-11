import os

DEFAULT_ASSETS_FOLDER = os.path.join(os.getcwd(), "asset_files")


class ConfigSections:
    KEEPER_CONTRACTS = 'keeper-contracts'


class BaseURLs:
    BASE_PROVIDER_URL = '/app/v1/provider'

