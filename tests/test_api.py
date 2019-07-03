#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import json

from aquarius.app.assets import validate_date_format
from aquarius.constants import BaseURLs
from aquarius.run import get_status, get_version
from tests.conftest import (json_before, json_dict, json_dict2, json_dict_no_metadata,
                            json_dict_no_valid_metadata, json_update, json_valid, test_assets)


def test_version(client):
    """Test version in root endpoint"""
    rv = client.get('/')
    assert json.loads(rv.data.decode('utf-8'))['software'] == 'Aquarius'
    assert json.loads(rv.data.decode('utf-8'))['version'] == get_version()


def test_health(client):
    """Test health check endpoint"""
    rv = client.get('/health')
    assert rv.data.decode('utf-8') == get_status()[0]


def test_create_ddo(client, base_ddo_url):
    """Test creation of asset"""
    rv = client.get(
        base_ddo_url + '/%s' % json_dict['id'],
        content_type='application/json')
    assert json_dict['id'] in json.loads(rv.data.decode('utf-8'))['id']
    assert json_dict['@context'] in json.loads(rv.data.decode('utf-8'))['@context']
    assert json_dict['service'][2]['type'] in json.loads(rv.data.decode('utf-8'))['service'][0][
        'type']


def test_upsert_ddo(client_with_no_data, base_ddo_url):
    """Test creation of asset"""
    put = client_with_no_data.put(base_ddo_url + '/%s' % json_dict['id'],
                                  data=json.dumps(json_dict2),
                                  content_type='application/json')
    rv = client_with_no_data.get(
        base_ddo_url + '/%s' % json.loads(put.data.decode('utf-8'))['id'],
        content_type='application/json')
    assert 201 == put.status_code
    assert json_dict['id'] in json.loads(rv.data.decode('utf-8'))['id']
    assert json_dict['@context'] in json.loads(rv.data.decode('utf-8'))['@context']
    assert json_dict['service'][2]['type'] in json.loads(rv.data.decode('utf-8'))['service'][0][
        'type']
    client_with_no_data.delete(
        base_ddo_url + '/%s' % json.loads(put.data.decode('utf-8'))['id'])


def test_post_with_no_ddo(client, base_ddo_url):
    post = client.post(base_ddo_url,
                       data=json.dumps(json_dict_no_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_post_with_no_valid_ddo(client, base_ddo_url):
    post = client.post(base_ddo_url,
                       data=json.dumps(json_dict_no_valid_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_update_ddo(client_with_no_data, base_ddo_url):
    client = client_with_no_data
    post = client.post(base_ddo_url,
                       data=json.dumps(json_before),
                       content_type='application/json')
    put = client.put(
        base_ddo_url + '/%s' % json.loads(post.data.decode('utf-8'))['id'],
        data=json.dumps(json_update),
        content_type='application/json')
    rv = client.get(
        base_ddo_url + '/%s' % json.loads(post.data.decode('utf-8'))['id'],
        content_type='application/json')
    assert 200 == put.status_code
    assert json_update['service'][2]['metadata']['curation']['numVotes'] == \
           json.loads(rv.data.decode('utf-8'))['service'][0]['metadata']['curation']['numVotes']
    assert json.loads(post.data.decode('utf-8'))['service'][0]['metadata']['base'][
               'checksum'] != \
           json.loads(rv.data.decode('utf-8'))['service'][0]['metadata']['base'][
               'checksum']
    client.delete(
        base_ddo_url + '/%s' % json.loads(post.data.decode('utf-8'))['id'])


def test_query_metadata(client, base_ddo_url):
    assert len(json.loads(client.post(base_ddo_url + '/query',
                                      data=json.dumps({"query": {}}),
                                      content_type='application/json').data.decode('utf-8'))[
                   'results']) == 2
    assert len(json.loads(client.post(base_ddo_url + '/query',
                                      data=json.dumps(
                                          {"query": {"price": ["14", "16"]}}),
                                      content_type='application/json').data.decode('utf-8'))[
                   'results']) == 1
    assert len(json.loads(client.get(base_ddo_url + '/query?text=Office',
                                     ).data.decode('utf-8'))['results']) == 1
    assert len(json.loads(
        client.get(base_ddo_url + '/query?text=112233445566778899',
                   ).data.decode('utf-8'))['results']) == 1
    try:
        num_assets = len(test_assets) + 2
        for a in test_assets:
            client.post(base_ddo_url,
                        data=json.dumps(a),
                        content_type='application/json')

        response = json.loads(
            client.get(base_ddo_url + '/query?text=white&page=1&offset=5', )
                .data.decode('utf-8')
        )
        assert response['page'] == 1
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == 5

        response = json.loads(
            client.get(base_ddo_url + '/query?text=white&page=3&offset=5', )
                .data.decode('utf-8')
        )
        assert response['page'] == 3
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == num_assets - (5 * (response['total_pages'] - 1))

        response = json.loads(
            client.get(base_ddo_url + '/query?text=white&page=4&offset=5', )
                .data.decode('utf-8')
        )
        assert response['page'] == 4
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == 0

    finally:
        for a in test_assets:
            client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % a['id'])


def test_delete_all(client_with_no_data, base_ddo_url):
    client_with_no_data.post(base_ddo_url,
                             data=json.dumps(json_dict),
                             content_type='application/json')
    client_with_no_data.post(base_ddo_url,
                             data=json.dumps(json_update),
                             content_type='application/json')
    assert len(json.loads(
        client_with_no_data.get(BaseURLs.BASE_AQUARIUS_URL + '/assets').data.decode('utf-8'))[
                   'ids']) == 2
    client_with_no_data.delete(base_ddo_url)
    assert len(json.loads(
        client_with_no_data.get(BaseURLs.BASE_AQUARIUS_URL + '/assets').data.decode('utf-8'))[
                   'ids']) == 0


def test_is_listed(client, base_ddo_url):
    assert len(json.loads(
        client.get(BaseURLs.BASE_AQUARIUS_URL + '/assets').data.decode('utf-8'))['ids']
               ) == 2

    client.put(
        base_ddo_url + '/%s' % json_dict['id'],
        data=json.dumps(json_dict2),
        content_type='application/json')
    assert len(json.loads(
        client.get(BaseURLs.BASE_AQUARIUS_URL + '/assets').data.decode('utf-8'))['ids']
               ) == 1
    assert len(json.loads(
        client.post(base_ddo_url + '/query',
                    data=json.dumps({"query": {"price": ["14", "16"]}}),
                    content_type='application/json').data.decode('utf-8')
    )['results']) == 1


def test_validate(client_with_no_data, base_ddo_url):
    post = client_with_no_data.post(base_ddo_url + '/validate',
                                    data=json.dumps({}),
                                    content_type='application/json')
    assert post.status_code == 200
    assert post.data == b'[{"message":"\'base\' is a required property","path":""}]\n'
    post = client_with_no_data.post(base_ddo_url + '/validate',
                                    data=json.dumps(json_valid),
                                    content_type='application/json')
    assert post.data == b'true\n'


def test_date_format_validator():
    date = '2016-02-08T16:02:20Z'
    assert validate_date_format(date) == (None, None)


def test_invalid_date():
    date = 'XXXX'
    assert validate_date_format(date) == (
        "Incorrect data format, should be '%Y-%m-%dT%H:%M:%SZ'", 400)
