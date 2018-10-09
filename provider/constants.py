class ConfigSections:
    OCEANBD = 'oceandb'
    KEEPER_CONTRACTS = 'keeper-contracts'
    RESOURCES = 'resources'


class BaseURLs:
    BASE_PROVIDER_URL = '/api/v1/provider'
    SWAGGER_URL = '/api/v1/docs'  # URL for exposing Swagger UI (without trailing '/')
    ASSETS_URL = BASE_PROVIDER_URL + '/assets'
