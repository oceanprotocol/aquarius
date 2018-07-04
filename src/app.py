import sys
import os

import hug
from hug.defaults import input_format

from ConfigOptions import ConfigOptions
from blockchain.ocean_contracts import OceanContracts
from constants import BaseURLs
import resources.assets as assets
from database.instance import get_oceandb_instance
from util import get_config_file, multipart, json_formatter

# :HACK: HACK ALERT
input_format['multipart/form-data'] = multipart
input_format['application/json'] = json_formatter


def create_app():
    app = hug.API(__name__)

    app.extend(assets, BaseURLs.BASE_PROVIDER_URL + '/assets')

    config_file = get_config_file()
    if config_file is not None and not os.path.isfile(config_file):
        print('"config" must point to a valid file.')
        sys.exit()

    get_oceandb_instance(config_file=config_file)
    dbconfig = ConfigOptions(config_file).getValue('dbconfig')
    print('dbconfig: %s' % dbconfig)
    dbconfig = os.path.abspath(dbconfig)
    db = get_oceandb_instance(dbconfig).instance
    print('Using oceandb plugin type: %s' % db.type)

    # OceanContracts()

    return app


app = create_app()


if __name__ == '__main__':
    app = create_app()
