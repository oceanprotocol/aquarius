#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

class ConfigSections:
    OCEANBD = 'oceandb'
    RESOURCES = 'resources'


class BaseURLs:
    BASE_AQUARIUS_URL = '/api/v1/aquarius'
    SWAGGER_URL = '/api/v1/docs'  # URL for exposing Swagger UI (without trailing '/')
    ASSETS_URL = BASE_AQUARIUS_URL + '/assets'
    POOLS_URL = BASE_AQUARIUS_URL + '/pools'


class Metadata:
    TITLE = 'Aquarius'
    DESCRIPTION = 'Aquarius provides an off-chain database store for metadata about data assets. ' \
                  'When running with our Docker images, it is exposed under:'
