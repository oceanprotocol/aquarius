import json
from provider.constants import BaseURLs
from tests.conftest import json_dict, json_dict_no_metadata, json_dict_no_valid_metadata, json_before, json_update


def test_create_asset(client):
    """Test creation of asset"""
    post = client.post(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata',
                       data=json.dumps(json_dict),
                       content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'],
        content_type='application/json')
    assert json_dict['base']['name'] in json.loads(rv.data.decode('utf-8'))['base']['name']
    client.delete(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'])


def test_post_with_no_metadata(client):
    post = client.post(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata',
                       data=json.dumps(json_dict_no_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_post_with_no_valid_metadata(client):
    post = client.post(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata',
                       data=json.dumps(json_dict_no_valid_metadata),
                       content_type='application/json')
    assert 400 == post.status_code


def test_update_asset_metadata(client):
    post = client.post(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata',
                       data=json.dumps(json_before),
                       content_type='application/json')
    client.put(
        BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'],
        data=json.dumps(json_update),
        content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'],
        content_type='application/json')
    assert json_update['curation']['rating'] == json.loads(rv.data.decode('utf-8'))['curation']['rating']
    assert json.loads(post.data.decode('utf-8'))['additionalInformation']['checksum'] != json.loads(rv.data.decode('utf-8'))['additionalInformation']['checksum']
    client.delete(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'])
