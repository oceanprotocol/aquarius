import json
from provider.constants import BaseURLs

json_dict = {"publisherId": "0x1",
             "metadata":{
                "base": {
                    "name": "UK Weather information 2011",
                    "description": "Weather information of UK including temperature and humidity",
                    "size": "3.1gb",
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "encoding": "UTF-8",
                    "compression": "zip",
                    "contentType": "text/csv",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,humidity\n"
                                   "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                    "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                    "links": [
                        {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                        {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                        {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                     ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity"

                },
                "curation": {
                    "rating": 0.93,
                    "numVotes": 123,
                    "schema": "Binary Votting"
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly"
                }
             },
             "assetId": "001"
             }
json_dict_no_metadata = {"publisherId": "0x2"}
json_dict_no_valid_metadata = {"publisherId": "0x4",
                               "metadata": {
                                   "base": {}
                               },
                               "assetId": "002"
                               }

json_before = {"publisherId": "0x6",
               "metadata":{
                "base": {
                    "name": "UK Weather information 2011",
                    "description": "Weather information of UK including temperature and humidity",
                    "size": "3.1gb",
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "encoding": "UTF-8",
                    "compression": "zip",
                    "contentType": "text/csv",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,humidity\n"
                                   "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                    "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                    "links": [
                        {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                        {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                        {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                     ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity"

                },
                "curation": {
                    "rating": 0,
                    "numVotes": 0,
                    "schema": "Binary Votting"
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly"
                }
             },
               "assetId": "003"}
json_update = {"publisherId": "0x6",
               "metadata": {
                   "base": {
                       "name": "UK Weather information 2011",
                       "description": "Weather information of UK including temperature and humidity",
                       "size": "3.1gb",
                       "dateCreated": "2012-02-01T10:55:11+00:00",
                       "author": "Met Office",
                       "license": "CC-BY",
                       "copyrightHolder": "Met Office",
                       "encoding": "UTF-8",
                       "compression": "zip",
                       "contentType": "text/csv",
                       "workExample": "stationId,latitude,longitude,datetime,temperature,humidity\n"
                                      "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                       "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                       "links": [
                           {
                               "sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                           {
                               "sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                           {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                       ],
                       "inLanguage": "en",
                       "tags": "weather, uk, 2011, temperature, humidity"

                   },
                   "curation": {
                       "rating": 0.8,
                       "numVotes": 1,
                       "schema": "Binary Votting"
                   },
                   "additionalInformation": {
                       "updateFrecuency": "yearly"
                   }
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
    assert json_dict['metadata']['base']['name'] in json.loads(rv.data.decode('utf-8'))['metadata']['base']['name']
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
    assert json_update['metadata']['curation']['rating'] == json.loads(rv.data.decode('utf-8'))['metadata']['curation']['rating']
    client.delete(BaseURLs.BASE_PROVIDER_URL + '/assets/metadata/%s' % json.loads(post.data.decode('utf-8'))['assetId'])
