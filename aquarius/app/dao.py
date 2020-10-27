#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging

import elasticsearch
from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import FullTextModel, QueryModel


class Dao(object):

    def __init__(self, oceandb=None, config_file=None):
        self.oceandb = oceandb or OceanDb(config_file).plugin

    def get_all_listed_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                if len(asset) == 1:
                    continue

                if self.is_listed(asset['service']):
                    asset_with_id.append(self.oceandb.read(asset['id']))
            except Exception as e:
                logging.error(f'Dao.get_all_listed_assets: {str(e)}')

        return asset_with_id

    def get_all_assets(self):
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                asset_with_id.append(self.oceandb.read(asset['id']))
            except Exception as e:
                logging.error(f'Dao.get_all_assets: {str(e)}')

        return asset_with_id

    def get(self, asset_id):
        try:
            asset = self.oceandb.read(asset_id)
        except elasticsearch.exceptions.NotFoundError as e:
            logging.error(f'Dao.get -- asset with id {asset_id} was not found, original error was:{str(e)}')
            raise

        except Exception as e:
            logging.error(f'Dao.get: {str(e)}')
            raise

        if asset is None or not self.is_listed(asset['service']):
            return None

        return asset

    def register(self, record, asset_id):
        return self.oceandb.write(record, asset_id)

    def update(self, record, asset_id):
        return self.oceandb.update(record, asset_id)

    def delete(self, asset_id):
        return self.oceandb.delete(asset_id)

    def delete_all(self):
        assets = self.oceandb.list()
        for asset in assets:
            try:
                self.delete(asset['id'])
            except Exception as e:
                logging.error(f'Dao.delete_all: {str(e)}')

    def query(self, query):
        query_list = []
        if isinstance(query, QueryModel):
            query_result, count = self.oceandb.query(query)
        elif isinstance(query, FullTextModel):
            query_result, count = self.oceandb.text_query(query)
        else:
            raise TypeError('Unrecognized `query` type %s' % type(query))

        for f in query_result:
            if 'service' in f:
                if self.is_listed(f['service']):
                    query_list.append(f)

        return query_list, count

    @staticmethod
    def is_listed(services):
        for service in services:
            if service['type'] == 'metadata':
                if 'curation' in service['attributes'] and 'isListed' in service['attributes']['curation']:
                    return service['attributes']['curation']['isListed']
