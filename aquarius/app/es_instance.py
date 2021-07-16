import os
import logging
import time
from elasticsearch import Elasticsearch

from aquarius.app.es_mapping import es_mapping

_DB_INSTANCE = None

logger = logging.getLogger(__name__)


def get_database_instance(config_file=None):
    global _DB_INSTANCE
    if _DB_INSTANCE is None:
        _DB_INSTANCE = ElasticsearchInstance(config_file)

    return _DB_INSTANCE


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
        username = get_value("db.username", "DB_USERNAME", None, config)
        password = get_value("db.password", "DB_PASSWORD", None, config)
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

            self._es.indices.create(index=index, ignore=400, body=es_mapping)

        except Exception as e:
            logging.info(f"Exception trying to connect... {e}")

    @property
    def es(self):
        return self._es

    @property
    def db_index(self):
        return self._index

    @property
    def instance(self):
        return self

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
        logger.debug("elasticsearch::read::{}".format(resource_id))
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
        if count_result is not None and count_result["count"] > 0:
            return count_result["count"]

        return 0

    def list(self, search_from=None, search_to=None, limit=None, chunk_size=100):
        """List all the objects saved in elasticsearch
        :param search_from: start offset of objects to return.
        :param search_to: last offset of objects to return.
        :param limit: max number of values to be returned.
        :param chunk_size: int size of each batch of objects
        :return: generator with all matching documents
        """
        logger.debug("elasticsearch::list")
        _body = {
            "sort": [
                {"_id": "asc"},
            ],
            "query": {"match_all": {}},
        }

        count = 0
        count_result = self.es.count(index=self.db_index)
        if count_result is not None and count_result["count"] > 0:
            count = count_result["count"]

        if not count:
            return []

        search_from = search_from if search_from is not None and search_from >= 0 else 0
        search_from = min(search_from, count - 1)
        search_to = (
            search_to if search_to is not None and search_to >= 0 else (count - 1)
        )
        limit = search_to - search_from + 1
        chunk_size = min(chunk_size, limit)

        _body["size"] = chunk_size
        processed = 0
        while processed < limit:
            body = _body.copy()
            body["from"] = search_from
            result = self.es.search(index=self.db_index, body=body)
            hits = result["hits"]["hits"]
            search_from += len(hits)
            processed += len(hits)
            for x in hits:
                yield x["_source"]

    def _mapping_to_sort(self, keys):
        for i in keys:
            mapping = (
                """{
                              "properties": {
                                "%s" : {
                                  "type": "text",
                                  "fields": {
                                    "keyword": {
                                      "type": "keyword"
                                    }
                                  }
                                }
                              }
                        }
            """
                % i
            )
            if self.es.indices.get_field_mapping(i)[self.db_index]["mappings"] == {}:
                self.es.indices.put_mapping(
                    index=self.db_index, body=mapping, doc_type="_doc"
                )

    def _sort_object(self, sort):
        try:
            o = []
            for key in sort.keys():
                last_k = key.split(".")[-1]
                field_mapping = self.es.indices.get_field_mapping(key)
                value = field_mapping[self.db_index]["mappings"]["_doc"][key][
                    "mapping"
                ][last_k]["type"]
                if value == "text":
                    o.append(
                        {key + ".keyword": ("asc" if sort.get(key) == 1 else "desc")},
                    )
                else:
                    o.append(
                        {key: ("asc" if sort.get(key) == 1 else "desc")},
                    )
            return o
        except Exception:
            raise Exception('Sort "{}" does not have a valid format.'.format(sort))