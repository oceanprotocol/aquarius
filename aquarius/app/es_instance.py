#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os
import time

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

_DB_INSTANCE = None

logger = logging.getLogger(__name__)


def get_value(value, env_var, default, config=None):
    if os.getenv(env_var) is not None:
        return os.getenv(env_var)

    if config is not None and value in config:
        return config[value]

    return default


class ElasticsearchInstance(object):
    def __init__(self, config=None):
        host = get_value("db.hostname", "DB_HOSTNAME", "localhost", config)
        port = int(get_value("db.port", "DB_PORT", 9200, config))
        username = get_value("db.username", "DB_USERNAME", "elastic", config)
        password = get_value("db.password", "DB_PASSWORD", "changeme", config)
        index = get_value("db.index", "DB_INDEX", "oceandb", config)
        ssl = self.str_to_bool(get_value("db.ssl", "DB_SSL", "false", config))
        verify_certs = self.str_to_bool(
            get_value("db.verify_certs", "DB_VERIFY_CERTS", "false", config)
        )
        ca_certs = get_value("db.ca_cert_path", "DB_CA_CERTS", None, config)
        client_key = get_value("db.client_key", "DB_CLIENT_KEY", None, config)
        client_cert = get_value("db.client_cert_path", "DB_CLIENT_CERT", None, config)
        self._index = index
        try:
            self._es = Elasticsearch(
                [host],
                http_auth=(username, password),
                port=port,
                use_ssl=ssl,
                verify_certs=verify_certs,
                ca_certs=ca_certs,
                client_cert=client_key,
                client_key=client_cert,
                maxsize=1000,
            )
            while self._es.ping() is False:
                logging.info("Trying to connect...")
                time.sleep(5)

            self._es.indices.create(index=index, ignore=400)

        except Exception as e:
            logging.info(f"Exception trying to connect... {e}")

    @property
    def es(self):
        return self._es

    @property
    def db_index(self):
        return self._index

    @staticmethod
    def str_to_bool(s):
        if s == "true":
            return True
        elif s == "false":
            return False
        else:
            raise ValueError

    def write(self, obj, resource_id=None):
        """Write obj in elasticsearch.
        :param obj: value to be written in elasticsearch.
        :param resource_id: id for the resource.
        :return: id of the transaction.
        """
        logger.debug("elasticsearch::write::{}".format(resource_id))
        if resource_id is not None:
            if self.es.exists(index=self.db_index, id=resource_id, doc_type="_doc"):
                raise ValueError(
                    'Resource "{}" already exists, use update instead'.format(
                        resource_id
                    )
                )

        return self.es.index(
            index=self.db_index,
            id=resource_id,
            body=obj,
            doc_type="_doc",
            refresh="wait_for",
        )["_id"]

    def read(self, resource_id):
        """Read object in elasticsearch using the resource_id.
        :param resource_id: id of the object to be read.
        :return: object value from elasticsearch.
        """
        # logger.debug("elasticsearch::read::{}".format(resource_id))
        return self.es.get(index=self.db_index, id=resource_id, doc_type="_doc")[
            "_source"
        ]

    def update(self, obj, resource_id):
        """Update object in elasticsearch using the resource_id.
        :param obj: new value
        :param resource_id: id of the object to be updated.
        :return: id of the object.
        """
        logger.debug("elasticsearch::update::{}".format(resource_id))
        return self.es.index(
            index=self.db_index,
            id=resource_id,
            body=obj,
            doc_type="_doc",
            refresh="wait_for",
        )["_id"]

    def delete_all(self):
        q = """{
            "query" : {
                "match_all" : {}
            }
        }"""
        self.es.delete_by_query("_all", q)

    def delete(self, resource_id):
        """Delete an object from elasticsearch.
        :param resource_id: id of the object to be deleted.
        :return:
        """
        logger.debug("elasticsearch::delete::{}".format(resource_id))
        if not self.es.exists(index=self.db_index, id=resource_id, doc_type="_doc"):
            raise ValueError(f"Resource {resource_id} does not exists")

        return self.es.delete(index=self.db_index, id=resource_id, doc_type="_doc")

    def count(self):
        count_result = self.es.count(index=self.db_index)
        if count_result is not None and count_result.get("count", 0) > 0:
            return count_result["count"]

        return 0

    def get(self, asset_id):
        try:
            asset = self.read(asset_id)
        except NotFoundError:
            logger.info(f"Asset with id {asset_id} was not found in ES.")
            raise

        except Exception as e:
            logger.error(f"get: {str(e)}")
            raise

        if asset is None or not self.is_listed(asset):
            return None

        return asset

    @staticmethod
    def is_listed(asset):
        if (
            "status" in asset
            and "isListed" in asset["status"]
            and not asset["status"]["isListed"]
        ):
            return False

        return True
