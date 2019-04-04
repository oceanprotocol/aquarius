#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging

from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import FullTextModel, QueryModel


class Dao(object):

    def __init__(self, config_file=None):
        self.oceandb = OceanDb(config_file).plugin

    def get_all_listed_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                if self.is_listed(asset['service']):
                    asset_with_id.append(self.oceandb.read(asset['id']))
            except Exception as e:
                logging.error(str(e))
                pass
        return asset_with_id

    def get_all_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                asset_with_id.append(self.oceandb.read(asset['id']))
            except Exception as e:
                logging.error(str(e))
                pass
        return asset_with_id

    def get(self, asset_id):
        try:
            asset = self.oceandb.read(asset_id)
        except Exception:
            asset = None
        if asset is None:
            return asset
        elif self.is_listed(asset['service']):
            return asset
        else:
            return None

    def register(self, record, asset_id):
        return self.oceandb.write(record, asset_id)

    def update(self, record, asset_id):
        return self.oceandb.update(record, asset_id)

    def delete(self, asset_id):
        return self.oceandb.delete(asset_id)

    def query(self, query):
        query_list = []
        count = 0
        if isinstance(query, QueryModel):
            for f in self.oceandb.query(query)[0]:
                if self.is_listed(f['service']):
                    query_list.append(f)
            count = self.oceandb.query(query)[1]
        elif isinstance(query, FullTextModel):
            for f in self.oceandb.text_query(query)[0]:
                if self.is_listed(f['service']):
                    query_list.append(f)
            count = self.oceandb.text_query(query)[1]
        return query_list, count

    @staticmethod
    def is_listed(services):
        for service in services:
            if service['type'] == 'Metadata':
                return service['metadata']['curation']['isListed']
