import json
from provider.constants import BaseURLs

json_dict = {"publisherId": "0x1",
             "metadata": {
                 "name": "name",
                 "links": ["link"],
                 "size": "size",
                 "format": "format",
                 "description": "description"
             },
             "assetId": "001"
             }
json_dict_no_metadata = {"publisherId": "0x0"}
json_dict_no_valid_metadata = {"publisherId": "0x0",
                               "metadata": {
                                   "name": "name"
                               },
                               "assetId": "002"
                               }

json_before = {"publisherId": "0x6",
               "metadata": {
                   "name": "name",
                   "links": ["link"],
                   "size": "size",
                   "format": "format",
                   "description": "description"
               },
               "assetId": "003"}
json_update = {"publisherId": "0x6",
               "metadata": {
                   "name": "nameUpdated",
                   "links": ["link"],
                   "size": "size",
                   "format": "format",
                   "description": "description"
               },
               "assetId": "003"}


def test_create_asset(client):
    """Test creation of asset"""
    post = client.post(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata',
                       data=json.dumps(json_dict),
                       content_type='application/json')
    rv = client.get(
        BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'],
        content_type='application/json')
    assert 'name' in json.loads(rv.data.decode('utf-8'))['data']['metadata']['name']
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
    assert 'nameUpdated' in json.loads(rv.data.decode('utf-8'))['data']['metadata']['name']
    client.delete(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'])
