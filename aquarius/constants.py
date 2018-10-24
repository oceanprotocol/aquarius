class ConfigSections:
    OCEANBD = 'oceandb'
    RESOURCES = 'resources'


class BaseURLs:
    BASE_AQUARIUS_URL = '/api/v1/aquarius'
    SWAGGER_URL = '/api/v1/docs'  # URL for exposing Swagger UI (without trailing '/')
    ASSETS_URL = BASE_AQUARIUS_URL + '/assets'
