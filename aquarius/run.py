#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
"""
This module is the entrypoint for statring the Aquarius component.
"""
import click
import configparser

from elasticsearch import Elasticsearch
from flask import jsonify, request
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint
import os

from aquarius.app.assets import assets
from aquarius.app.chains import chains
from aquarius.app.validation import validation
from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import get_bool_env_value
from aquarius.config import Config, get_version
from aquarius.constants import BaseURLs, Metadata
from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.util import setup_web3
from aquarius.myapp import app
from aquarius.rbac import RBAC

config = Config(filename=app.config["AQUARIUS_CONFIG_FILE"])
aquarius_url = config.aquarius_url
es_instance = ElasticsearchInstance(app.config["AQUARIUS_CONFIG_FILE"])


@app.before_request
def set_rbac_headers():
    if os.getenv("RBAC_SERVER_URL"):
        RBAC.set_headers(request)


@app.route("/")
def version():
    """
    Returns:
        json object as follows:
        ```JSON
            {
                "plugin":"elasticsearch",
                "software":"Aquarius",
                "version":"2.2.12"
            }
        ```
    """
    info = dict()
    info["software"] = Metadata.TITLE
    info["version"] = get_version()
    info["plugin"] = config.module
    return jsonify(info)


@app.route("/health")
def health():
    """
    Returns conntection db status with mongodb or elasticsearch.
    """
    return get_status()


@app.route("/spec")
def spec():
    """
    Returns the information about supported endpoints generated through swagger. Also returns version info, database connection status.
    """
    swag = swagger(app)
    swag["info"]["version"] = get_version()
    swag["info"]["title"] = Metadata.TITLE
    swag["info"]["description"] = Metadata.DESCRIPTION + "`" + aquarius_url + "`."
    swag["info"]["connected"] = get_status()
    # swag['basePath'] = BaseURLs.BASE_AQUARIUS_URL
    return jsonify(swag)


# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    BaseURLs.SWAGGER_URL,
    aquarius_url + "/spec",
    config={"app_name": "Test application"},  # Swagger UI config overrides
)

# Register blueprint at URL
app.register_blueprint(swaggerui_blueprint, url_prefix=BaseURLs.SWAGGER_URL)
app.register_blueprint(assets, url_prefix=BaseURLs.ASSETS_URL)
app.register_blueprint(chains, url_prefix=BaseURLs.CHAINS_URL)
app.register_blueprint(validation, url_prefix=BaseURLs.VALIDATION_URL)


@app.cli.command("force_set_block")
@click.argument("chain_id")
@click.argument("block_number")
def force_set_block(chain_id, block_number):
    index_name = "events_last_block_" + str(chain_id)
    other_db_index = f"{es_instance.db_index}_plus"
    record = {"last_block": block_number}

    es_instance.es.index(
        index=other_db_index,
        id=index_name,
        body=record,
        doc_type="_doc",
        refresh="wait_for",
    )["_id"]

    print("OK")


def get_status():
    if Elasticsearch(config.db_url).ping():
        return "Elasticsearch connected", 200
    else:
        return "Not connected to any database", 400


# Start events monitoring if required
if get_bool_env_value("EVENTS_ALLOW", 0):
    config_file = app.config["AQUARIUS_CONFIG_FILE"]
    monitor = EventsMonitor(setup_web3(config_file), config_file)
    monitor.start_events_monitor()


if __name__ == "__main__":
    if isinstance(config.aquarius_url.split(":")[-1], int):
        app.run(
            host=config.aquarius_url.split(":")[1],
            port=config.aquarius_url.split(":")[-1],
        )
    else:
        app.run()
