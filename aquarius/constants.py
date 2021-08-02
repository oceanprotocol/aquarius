#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#


class ConfigSections:
    """
    This class contains values for:
        1. `OCEANBD`
        2. `RESOURCES`
    """

    OCEANBD = "oceandb"
    RESOURCES = "resources"


class BaseURLs:
    """
    This class contains values for:
        1. `BASE_AQUARIUS_URL`
        2. `SWAGGER_URL`
        3. `ASSETS_URL`
        4. `POOLS_URL`
    """

    BASE_AQUARIUS_URL = "/api/v1/aquarius"
    SWAGGER_URL = "/api/v1/docs"  # URL for exposing Swagger UI (without trailing '/')
    ASSETS_URL = BASE_AQUARIUS_URL + "/assets"
    CHAINS_URL = BASE_AQUARIUS_URL + "/chains"


class Metadata:
    """
    This class stores values for:
        1.`TITLE`
        2.`DESCRIPTION`
    """

    TITLE = "Aquarius"
    DESCRIPTION = (
        "Aquarius provides an off-chain database store for metadata about data assets. "
        "When running with our Docker images, it is exposed under:"
    )
