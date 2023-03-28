#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
from pathlib import Path
import pkg_resources
import rdflib

from flask import Blueprint, jsonify

from aquarius.ddo_checker.conversion import graph_to_dict
from aquarius.ddo_checker.shacl_checker import CURRENT_VERSION, ALLOWED_VERSIONS

from aquarius.log import setup_logging
from aquarius.myapp import app

setup_logging()
validation = Blueprint("validation", __name__)
logger = logging.getLogger("aquarius")


@validation.route(
    "/schema/<version?>", defaults={"version": CURRENT_VERSION}, methods=["GET"]
)
def schema(version):
    """Get validation version description
    ---
    tags:
      - validation
    responses:
      200:
        description: validation schema json.
      404:
        description: schema version not found
      500:
        description: server error
    """
    try:
        if version not in ALLOWED_VERSIONS:
            return jsonify(erorr="Schema version not found."), 404

        path = "ddo_checker/shacl_schemas/v4/remote_" + version + ".ttl"
        schema_file = Path(
            pkg_resources.resource_filename("aquarius", path)
        ).read_text()
        rulesGraph = rdflib.Graph().parse(data=schema_file)
        result = graph_to_dict(rulesGraph)
    except Exception as e:
        msg = f"Error in schema validation exposition: {str(e)}"
        logger.error(msg)
        return jsonify(error=msg), 500
