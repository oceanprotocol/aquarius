#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from unittest.mock import patch

import pytest

from aquarius.app.es_instance import ElasticsearchInstance
from aquarius.myapp import app

es_instance = ElasticsearchInstance()


def test_str_to_bool():
    assert es_instance.str_to_bool("true") is True
    assert es_instance.str_to_bool("false") is False
    with pytest.raises(ValueError):
        es_instance.str_to_bool("something_else")


def test_write_duplicate():
    with pytest.raises(ValueError):
        with patch("elasticsearch.Elasticsearch.exists") as mock:
            mock.return_value = True
            es_instance.write({}, "not_none")


def test_delete():
    with patch("elasticsearch.Elasticsearch.delete_by_query") as mock:
        es_instance.delete_all()
        mock.assert_called_once()

    with patch("elasticsearch.Elasticsearch.delete") as mock_delete, patch(
        "elasticsearch.Elasticsearch.exists"
    ) as mock_exists:
        mock_exists.return_value = True
        es_instance.delete(1)
        mock_delete.assert_called_once()

    with pytest.raises(ValueError):
        with patch("elasticsearch.Elasticsearch.exists") as mock:
            mock.return_value = False
            es_instance.delete(1)


def test_count():
    with patch("elasticsearch.Elasticsearch.count") as mock:
        mock.return_value = None
        assert es_instance.count() == 0

    with patch("elasticsearch.Elasticsearch.count") as mock:
        mock.return_value = {"count": 10}
        assert es_instance.count() == 10


def test_get():
    with pytest.raises(Exception):
        with patch("aquarius.app.es_instance.ElasticsearchInstance.read") as mock:
            mock.side_effect = Exception()
            es_instance.get(1)

    with patch("aquarius.app.es_instance.ElasticsearchInstance.read") as mock:
        mock.return_value = None
        assert es_instance.get(1) is None


def test_is_listed():
    mock_asset = {"missing status": "test"}
    assert es_instance.is_listed(mock_asset) is True

    mock_asset = {"status": {}}
    assert es_instance.is_listed(mock_asset) is True

    mock_asset = {"status": {"isListed": True}}
    assert es_instance.is_listed(mock_asset) is True

    mock_asset = {"status": {"isListed": False}}
    assert es_instance.is_listed(mock_asset) is False
