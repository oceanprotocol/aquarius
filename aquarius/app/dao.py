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
                    asset_with_id.append(asset)
            except Exception as e:
                logging.error(f'Dao.get_all_listed_assets: {str(e)}')

        return asset_with_id

    def get_all_assets(self):
        return [a for a in self.oceandb.list()]

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

    def run_es_query(self, query, sort, page, offset, text=None):
        """do an elasticsearch native query.

        The query is expected to be in the elasticsearch search format.

        :return: list of objects that match the query.
        """
        assert page >= 1, 'page value %s is invalid' % page

        logging.debug(f'elasticsearch::query::{query}, text {text}')
        if sort is not None:
            self.oceandb._mapping_to_sort(sort.keys())
            sort = self.oceandb._sort_object(sort)
        else:
            sort = [{"_id": "asc"}]

        if text:
            sort = [{"_score": "desc"}] + sort
            if isinstance(text, str):
                text = [text]

            text = [t.strip() for t in text]
            text = [t.replace('did:op:', '0x') for t in text if t]

        if not query:
            query = {'match_all': {}}

        body = {
            'sort': sort,
            'from': (page - 1) * offset,
            'size': offset,
            'query': query
        }
        logging.info(f'running query: {body}')
        page = self.oceandb.driver.es.search(
            index=self.oceandb.driver.db_index,
            body=body,
            q=text or None
        )

        object_list = []
        for x in page['hits']['hits']:
            object_list.append(x['_source'])

        return object_list, page['hits']['total']
