#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

import logging

import elasticsearch
from oceandb_driver_interface import OceanDb
from oceandb_driver_interface.search_model import FullTextModel, QueryModel
from aquarius.app.util import rename_metadata_keys


class Dao(object):
    def __init__(self, oceandb=None, config_file=None):
        self.oceandb = oceandb or OceanDb(config_file).plugin

    def get_all_listed_assets(self):
        return list(self.oceandb.list())

    def get_all_assets(self):
        return [a for a in self.oceandb.list()]

    def get(self, asset_id):
        try:
            asset = self.oceandb.read(asset_id)
        except elasticsearch.exceptions.NotFoundError as e:
            logging.error(
                f"Dao.get -- asset with id {asset_id} was not found, original error was:{str(e)}"
            )
            raise

        except Exception as e:
            logging.error(f"Dao.get: {str(e)}")
            raise

        if asset is None or not self.is_listed(asset["service"]):
            return None

        return asset

    def register(self, record, asset_id):
        return self.oceandb.write(record, asset_id)

    def update(self, record, asset_id):
        return self.oceandb.update(record, asset_id)

    def delete(self, asset_id):
        return self.oceandb.delete(asset_id)

    def delete_all(self):
        if hasattr(self.oceandb, "delete_all"):
            self.oceandb.delete_all()
        else:
            assets = self.oceandb.list()
            for asset in assets:
                try:
                    self.delete(asset["id"])
                except Exception as e:
                    logging.error(f"Dao.delete_all: {str(e)}")

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

    def run_es_query(self, data, with_metadata=False):
        """do an elasticsearch native query.

        The query is expected to be in the elasticsearch search format.

        :return: list of objects that match the query.
        """
        page = data.get("page", 1)
        assert page >= 1, "page value %s is invalid" % page

        sort = data.get("sort")
        if sort is not None:
            self.oceandb._mapping_to_sort(sort.keys())
            sort = self.oceandb._sort_object(sort)
        else:
            sort = [{"_id": "asc"}]

        query = data.get("query")
        if not query:
            query = {"match_all": {}}

        offset = data.get("offset", 0)
        body = {
            "sort": sort,
            "from": (page - 1) * offset,
            "size": offset,
            "query": query,
        }

        logging.info(f"running query: {body}")
        page = self.oceandb.driver.es.search(
            index=self.oceandb.driver.db_index, body=body
        )

        object_list = []
        for x in page["hits"]["hits"]:
            object_list.append(x["_source"])

        if not with_metadata:
            return object_list, page["hits"]["total"]

        body = {
            "size": 0,
            "query": query,
            "aggs": {
                "licenses": {
                    "terms": {"field": "service.attributes.main.license.keyword"}
                },
                "tags": {
                    "terms": {
                        "field": "service.attributes.additionalInformation.tags.keyword"
                    }
                },
            },
        }
        logging.info(f"running metadata query: {body}")
        metadata = self.oceandb.driver.es.search(
            index=self.oceandb.driver.db_index, body=body
        )
        metadata = {
            key: rename_metadata_keys(value["buckets"])
            for key, value in metadata["aggregations"].items()
        }

        return object_list, page["hits"]["total"], metadata
