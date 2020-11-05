#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging

import elasticsearch
from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import FullTextModel, QueryModel


class Dao(object):

    def __init__(self, oceandb=None, config_file=None):
        """
        Initialize the configuration.

        Args:
            self: (todo): write your description
            oceandb: (todo): write your description
            config_file: (str): write your description
        """
        self.oceandb = oceandb or OceanDb(config_file).plugin

    def get_all_listed_assets(self):
        """
        Stub

        Args:
            self: (todo): write your description
        """
        assets = self.oceandb.list()
        asset_with_id = []
        for asset in assets:
            try:
                if len(asset) == 1:
                    continue

                if self.is_listed(asset['service']):
                    asset_with_id.append(asset)
            except Exception as e:
                logging.error(f'Dao.get_all_listed_assets: {str(e)}')

        return asset_with_id

    def get_all_assets(self):
        """
        Return all assets.

        Args:
            self: (todo): write your description
        """
        return [a for a in self.oceandb.list()]

    def get(self, asset_id):
        """
        Retrieve an asset by its id.

        Args:
            self: (todo): write your description
            asset_id: (str): write your description
        """
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
        """
        Register a record.

        Args:
            self: (todo): write your description
            record: (todo): write your description
            asset_id: (str): write your description
        """
        return self.oceandb.write(record, asset_id)

    def update(self, record, asset_id):
        """
        Update an existing record

        Args:
            self: (todo): write your description
            record: (todo): write your description
            asset_id: (str): write your description
        """
        return self.oceandb.update(record, asset_id)

    def delete(self, asset_id):
        """
        Deletes the given asset.

        Args:
            self: (todo): write your description
            asset_id: (str): write your description
        """
        return self.oceandb.delete(asset_id)

    def delete_all(self):
        """
        Delete all assets.

        Args:
            self: (todo): write your description
        """
        if hasattr(self.oceandb, 'delete_all'):
            self.oceandb.delete_all()
        else:
            assets = self.oceandb.list()
            for asset in assets:
                try:
                    self.delete(asset['id'])
                except Exception as e:
                    logging.error(f'Dao.delete_all: {str(e)}')

    def query(self, query):
        """
        Execute a query.

        Args:
            self: (todo): write your description
            query: (str): write your description
        """
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
        """
        Return true if the service is installed.

        Args:
            services: (list): write your description
        """
        for service in services:
            if service['type'] == 'metadata':
                if 'curation' in service['attributes'] and 'isListed' in service['attributes']['curation']:
                    return service['attributes']['curation']['isListed']
