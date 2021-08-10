#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

import logging
import elasticsearch

from aquarius.app.es_instance import ElasticsearchInstance


class Dao(object):
    def __init__(self, config_file=None):
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

    @staticmethod
    def is_listed(services):
        for service in services:
            if service["type"] == "metadata":
                if (
                    "curation" in service["attributes"]
                    and "isListed" in service["attributes"]["curation"]
                ):
                    return service["attributes"]["curation"]["isListed"]
