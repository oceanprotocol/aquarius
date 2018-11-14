import json

from aquarius.constants import BaseURLs
from aquarius.run import get_version
from tests.conftest import json_dict, json_dict_no_metadata, json_dict_no_valid_metadata, json_before, json_update


def test_version(client):
    """Test version in root endpoint"""
    rv = client.get('/')
    assert json.loads(rv.data.decode('utf-8'))['software'] == 'Aquarius'
    assert json.loads(rv.data.decode('utf-8'))['version'] == get_version()


def test_create_ddo(client):
    """Test creation of asset"""
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_dict),
                       content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'],
        content_type='application/json')
    assert json_dict['id'] in json.loads(rv.data.decode('utf-8'))['id']
    assert json_dict['@context'] in json.loads(rv.data.decode('utf-8'))['@context']
    assert json_dict['service'][2]['type'] in json.loads(rv.data.decode('utf-8'))['service'][2]['type']
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'])


def test_upsert_ddo(client):
    """Test creation of asset"""
    put = client.put(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json_dict['id'],
                     data=json.dumps(json_dict),
                     content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(put.data.decode('utf-8'))['id'],
        content_type='application/json')
    assert 201 == put.status_code
    assert json_dict['id'] in json.loads(rv.data.decode('utf-8'))['id']
    assert json_dict['@context'] in json.loads(rv.data.decode('utf-8'))['@context']
    assert json_dict['service'][2]['type'] in json.loads(rv.data.decode('utf-8'))['service'][2]['type']
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(put.data.decode('utf-8'))['id'])


def test_post_with_no_ddo(client):
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_dict_no_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_post_with_no_valid_ddo(client):
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_dict_no_valid_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_update_ddo(client):
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_before),
                       content_type='application/json')
    put = client.put(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'],
        data=json.dumps(json_update),
        content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'],
        content_type='application/json')
    assert 200 == put.status_code
    assert json_update['service'][2]['metadata']['curation']['numVotes'] == \
           json.loads(rv.data.decode('utf-8'))['service'][2]['metadata']['curation']['numVotes']
    assert json.loads(post.data.decode('utf-8'))['service'][2]['metadata']['additionalInformation']['checksum'] != \
           json.loads(rv.data.decode('utf-8'))['service'][2]['metadata']['additionalInformation']['checksum']
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'])


def test_query_metadata(client):
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_update),
                       content_type='application/json')
    post2 = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                        data=json.dumps(json_dict),
                        content_type='application/json')
    assert len(json.loads(client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/query',
                                      data=json.dumps({"query": {}}),
                                      content_type='application/json').data.decode('utf-8'))) == 2
    assert len(json.loads(client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/query',
                                      data=json.dumps({"query": {"id": "did:op:123456789abcdefghi"}}),
                                      content_type='application/json').data.decode('utf-8'))) == 1
    assert len(json.loads(client.get(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/query?text=Office',
                                     ).data.decode('utf-8'))) == 2
    assert len(json.loads(client.get(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/query?text=112233445566778899',
                                     ).data.decode('utf-8'))) == 1
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'])
    client.delete(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post2.data.decode('utf-8'))['id'])
