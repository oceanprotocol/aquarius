#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import configparser
import os

from elasticsearch import Elasticsearch
from flask import jsonify
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint
from ocean_lib.config import Config as OceanConfig
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.web3_provider import Web3Provider
from pymongo import MongoClient

from aquarius.app.assets import assets
from aquarius.app.pools import pools
from aquarius.config import Config
from aquarius.constants import BaseURLs, Metadata
from aquarius.events.util import get_artifacts_path
from aquarius.myapp import app
from aquarius.events.events_monitor import EventsMonitor

config = Config(filename=app.config['CONFIG_FILE'])
aquarius_url = config.aquarius_url


def get_version():
    conf = configparser.ConfigParser()
    conf.read('.bumpversion.cfg')
    return conf['bumpversion']['current_version']


@app.route("/")
def version():
    info = dict()
    info['software'] = Metadata.TITLE
    info['version'] = get_version()
    info['plugin'] = config.module
    return jsonify(info)


@app.route("/health")
def health():
    return get_status()


@app.route("/spec")
def spec():
    swag = swagger(app)
    swag['info']['version'] = get_version()
    swag['info']['title'] = Metadata.TITLE
    swag['info']['description'] = Metadata.DESCRIPTION + '`' + aquarius_url + '`.'
    swag['info']['connected'] = get_status()
    # swag['basePath'] = BaseURLs.BASE_AQUARIUS_URL
    return jsonify(swag)


# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    BaseURLs.SWAGGER_URL,
    aquarius_url + '/spec',
    config={  # Swagger UI config overrides
        'app_name': "Test application"
    },
)

# Register blueprint at URL
app.register_blueprint(swaggerui_blueprint, url_prefix=BaseURLs.SWAGGER_URL)
app.register_blueprint(assets, url_prefix=BaseURLs.ASSETS_URL)
app.register_blueprint(pools, url_prefix=BaseURLs.POOLS_URL)


def get_status():
    if config.get('oceandb', 'module') == 'elasticsearch':
        if Elasticsearch(config.db_url).ping():
            return 'Elasticsearch connected', 200
        else:
            return 'Not connected to any database', 400
    elif config.get('oceandb', 'module') == 'mongodb':
        if MongoClient(config.db_url).get_database(config.get('oceandb', 'db.name')).command(
                'ping'):
            return 'Mongodb connected', 200
        else:
            return 'Not connected to any database', 400
    else:
        return 'Not connected to any database', 400


# Start events monitoring if required
if bool(int(os.environ.get('EVENTS_ALLOW', '0'))):
    _config = OceanConfig(app.config['CONFIG_FILE'])
    ConfigProvider.set_config(_config)
    from ocean_lib.ocean.util import get_web3_connection_provider

    rpc = os.environ.get('EVENTS_RPC', '')
    Web3Provider.init_web3(provider=get_web3_connection_provider(rpc))
    ContractHandler.set_artifacts_path(get_artifacts_path())

    monitor = EventsMonitor(
        Web3Provider.get_web3(),
        app.config['CONFIG_FILE']
    )
    monitor.start_events_monitor()


if __name__ == '__main__':
    if isinstance(config.aquarius_url.split(':')[-1], int):
        app.run(host=config.aquarius_url.split(':')[1],
                port=config.aquarius_url.split(':')[-1])
    else:
        app.run()
