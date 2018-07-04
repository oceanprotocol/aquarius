import os

import json
from oceandb_driver_interface import OceanDb

from ConfigOptions import ConfigOptions


_OCEAN_DB_INSTANCE = None


def sanitize_record(data_record):
    if '_id' in data_record:
        data_record.pop('_id')
    return json.dumps(data_record)


def get_oceandb_instance(database_name='ocean', config_file=None):
    global _OCEAN_DB_INSTANCE
    if _OCEAN_DB_INSTANCE is None:
        _OCEAN_DB_INSTANCE = _OceanDatabaseInstance(database_name, config_file)

    return _OCEAN_DB_INSTANCE


class _OceanDatabaseInstance(object):
    def __init__(self, db_name, config_file=None):
        dbconfig = ConfigOptions(config_file).getValue('dbconfig')
        dbconfig = os.path.abspath(dbconfig)
        self.db = OceanDb(dbconfig).plugin

    @property
    def instance(self):
        return self.db
