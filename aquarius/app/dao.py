#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

import logging
import elasticsearch

from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.app.util import rename_metadata_keys


class Dao(object):
    def __init__(self, config_file=None):
        self.oceandb = OceanDb(config_file).plugin
        self.es_instance = ElasticsearchInstance(config_file)

    def get_all_listed_assets(self):
        return list(self.es_instance.list())

    def get_all_assets(self):
        return [a for a in self.es_instance.list()]

    def get(self, asset_id):
        try:
            asset = self.es_instance.read(asset_id)
        except elasticsearch.exceptions.NotFoundError:
            logging.info(f"Dao.get: asset with id {asset_id} was not found in ES.")
            raise

        except Exception as e:
            logging.error(f"Dao.get: {str(e)}")
            raise

        if asset is None or not self.is_listed(asset["service"]):
            return None

        return asset

    def register(self, record, asset_id):
        return self.es_instance.write(record, asset_id)

    def update(self, record, asset_id):
        return self.es_instance.update(record, asset_id)

    def delete(self, asset_id):
        return self.es_instance.delete(asset_id)

    def delete_all(self):
        self.es_instance.delete_all()

    def query(self, query):
        query_list = []
        if isinstance(query, QueryModel):
            query_result, count = self.oceandb.query(query)
        elif isinstance(query, FullTextModel):
            query_result, count = self.oceandb.text_query(query)
        else:
            raise TypeError("Unrecognized `query` type %s" % type(query))

        for f in query_result:
            if "service" in f:
                if self.is_listed(f["service"]):
                    query_list.append(f)

        return query_list, count

    @staticmethod
    def is_listed(services):
        for service in services:
            if service["type"] == "metadata":
                if (
                    "curation" in service["attributes"]
                    and "isListed" in service["attributes"]["curation"]
                ):
                    return service["attributes"]["curation"]["isListed"]

    def refine_query_parameters(self, data):
        page = data.get("page", 1)
        assert page >= 1, "page value %s is invalid" % page

        sort = data.get("sort")
        if sort is not None:
            self.oceandb._mapping_to_sort(sort.keys())
            sort = self.oceandb._sort_object(sort)

        query = data.get("query")
        if not query:
            query = {"match_all": {}}

        offset = data.get("offset", 0)

        return query, sort, page, offset

    def run_es_query(self, data):
        """do an elasticsearch native query.

        The query is expected to be in the elasticsearch search format.

        :return: list of objects that match the query.
        """
        query, sort, page, offset = self.refine_query_parameters(data)
        body = {"from": (page - 1) * offset, "size": offset, "query": query}
        if sort:
            body["sort"] = sort

        logging.info(f"running query: {body}")
        page = self.es_instance.es.search(index=self.es_instance.db_index, body=body)

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        return object_list, page["hits"]["total"]
