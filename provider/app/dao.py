import logging

from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import QueryModel, FullTextModel


class Dao(object):

    def __init__(self, config_file=None):
        self.oceandb = OceanDb(config_file).plugin

    def get_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                asset_with_id.append(self.oceandb.read(asset['assetId']))
            except Exception as e:
                logging.error(str(e))
                pass
        return asset_with_id

    def get(self, asset_id):
        return self.oceandb.read(asset_id)

    def register(self, record, asset_id):
        return self.oceandb.write(record, asset_id)

    def update(self, record, asset_id):
        return self.oceandb.update(record, asset_id)

    def delete(self, asset_id):
        return self.oceandb.delete(asset_id)

    def query(self, query):
        query_list = []
        if isinstance(query, QueryModel):
            for f in self.oceandb.query(query):
                query_list.append(f)
        elif isinstance(query, FullTextModel):
            for f in self.oceandb.text_query(query):
                query_list.append(f)
        return query_list
