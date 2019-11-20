#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import json

from aquarius.app.assets import validate_date_format
from aquarius.constants import BaseURLs
from aquarius.run import get_status, get_version
from tests.conftest import (json_before, json_dict, json_dict2, json_dict_no_metadata,
                            json_dict_no_valid_metadata, json_update, json_valid, test_assets)


def run_request_get_data(client_method, url, data=None):
    _response = run_request(client_method, url, data)
    if _response and _response.data:
        return json.loads(_response.data.decode('utf-8'))

    return None


def run_request(client_method, url, data=None):
    if data is None:
        _response = client_method(url, content_type='application/json')
    else:
        _response = client_method(
            url, data=json.dumps(data), content_type='application/json'
        )

    return _response


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
    rv = run_request_get_data(client.get, base_ddo_url + '/%s' % json_dict['id'])
    assert json_dict['id'] in rv['id']
    assert json_dict['@context'] in rv['@context']
    assert json_dict['service'][2]['type'] in rv['service'][0]['type']


def test_upsert_ddo(client_with_no_data, base_ddo_url):
    """Test creation of asset"""
    put = client_with_no_data.put(base_ddo_url + '/%s' % json_dict['id'],
                                  data=json.dumps(json_dict2),
                                  content_type='application/json')
    assert put.status_code in (200, 201), 'Failed to register/update asset.'

    rv = run_request_get_data(
        client_with_no_data.get,
        base_ddo_url + '/%s' % json.loads(put.data.decode('utf-8'))['id']
    )
    assert 201 == put.status_code
    assert json_dict['id'] in rv['id']
    assert json_dict['@context'] in rv['@context']
    assert json_dict['service'][2]['type'] in rv['service'][0]['type']
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
    post = run_request_get_data(client.post, base_ddo_url, data=json_before)
    put = client.put(
        base_ddo_url + '/%s' % post['id'],
        data=json.dumps(json_update),
        content_type='application/json')
    assert 200 == put.status_code, 'Failed to update asset'
    rv = client.get(
        base_ddo_url + '/%s' % post['id'],
        content_type='application/json')
    fetched_ddo = json.loads(rv.data.decode('utf-8'))
    assert json_update['service'][2]['attributes']['curation']['numVotes'] == \
        fetched_ddo['service'][0]['attributes']['curation']['numVotes']

    put = client.put(
        base_ddo_url + '/%s' % post['id'],
        data=json.dumps(fetched_ddo),
        content_type='application/json')
    assert 200 == put.status_code, 'Failed to update asset without changes.'

    client.delete(
        base_ddo_url + '/%s' % post['id'])


def test_query_metadata(client, base_ddo_url):

    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {}})['results']) == 2

    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': "UK"}})['results']) == 1

    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': "weather"}})['results']) == 1
    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': ["UK"]}})['results']) == 1
    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': "uK"}})['results']) == 1
    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': ["UK", "temperature"]}})['results']) == 1
    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': ["ocean protocol", "Vision", "paper"]}})['results']) == 1
    assert len(run_request_get_data(
        client.post, base_ddo_url + '/query', {"query": {'text': ["UK", "oceAN"]}})['results']) == 2

    assert len(
        run_request_get_data(client.post, base_ddo_url + '/query',
                             {"query": {"price": ["14", "16"]}}
                             )['results']
    ) == 1
    assert len(
        run_request_get_data(client.get, base_ddo_url + '/query?text=Office'
                             )['results']
    ) == 1
    assert len(
        run_request_get_data(client.get,
                             base_ddo_url + '/query?text=112233445566778899')['results']
    ) == 1

    try:
        num_assets = len(test_assets) + 2
        for a in test_assets:
            client.post(base_ddo_url,
                        data=json.dumps(a),
                        content_type='application/json')

        response = run_request_get_data(client.get, base_ddo_url + '/query?text=white&page=1&offset=5')
        assert response['page'] == 1
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == 5

        response = run_request_get_data(client.get, base_ddo_url + '/query?text=white&page=3&offset=5')
        assert response['page'] == 3
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == num_assets - (5 * (response['total_pages'] - 1))

        response = run_request_get_data(client.get, base_ddo_url + '/query?text=white&page=4&offset=5')
        assert response['page'] == 4
        assert response['total_pages'] == int(num_assets / 5) + int(num_assets % 5 > 0)
        assert response['total_results'] == num_assets
        assert len(response['results']) == 0

    finally:
        for a in test_assets:
            client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % a['id'])


def test_delete_all(client_with_no_data, base_ddo_url):
    run_request(client_with_no_data.post, base_ddo_url, data=json_dict)
    run_request(client_with_no_data.post, base_ddo_url, data=json_update)
    assert len(run_request_get_data(client_with_no_data.get, BaseURLs.BASE_AQUARIUS_URL + '/assets')['ids']) == 2
    client_with_no_data.delete(base_ddo_url)
    assert len(run_request_get_data(client_with_no_data.get, BaseURLs.BASE_AQUARIUS_URL + '/assets')['ids']) == 0


def test_is_listed(client, base_ddo_url):
    assert len(run_request_get_data(client.get, BaseURLs.BASE_AQUARIUS_URL + '/assets')['ids']) == 2

    run_request(client.put, base_ddo_url + '/%s' % json_dict['id'], data=json_dict2)
    assert len(run_request_get_data(client.get, BaseURLs.BASE_AQUARIUS_URL + '/assets')['ids']) == 1
    assert len(run_request_get_data(client.post, base_ddo_url + '/query', data={"query": {"price": ["14", "16"]}})['results']) == 1


def test_validate(client_with_no_data, base_ddo_url):
    post = run_request(client_with_no_data.post, base_ddo_url + '/validate', data={})
    assert post.status_code == 200
    assert post.data == b'[{"message":"\'main\' is a required property","path":""}]\n'
    post = run_request(client_with_no_data.post, base_ddo_url + '/validate', data=json_valid)
    assert post.data == b'true\n'


def test_date_format_validator():
    date = '2016-02-08T16:02:20Z'
    assert validate_date_format(date) == (None, None)


def test_invalid_date():
    date = 'XXXX'
    assert validate_date_format(date) == (
        "Incorrect data format, should be '%Y-%m-%dT%H:%M:%SZ'", 400)
