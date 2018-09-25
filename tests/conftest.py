import pytest

from provider.run import app

app = app


@pytest.fixture
def client():
    client = app.test_client()
    yield client


json_dict = {"publisherId": "0x1",
             "base": {
                 "name": "UK Weather information 2011",
                 "description": "Weather information of UK including temperature and humidity",
                 "size": "3.1gb",
                 "author": "Met Office",
                 "license": "CC-BY",
                 "copyrightHolder": "Met Office",
                 "encoding": "UTF-8",
                 "compression": "zip",
                 "contentType": "text/csv",
                 "workExample": "stationId,latitude,longitude,datetime,temperature,humidity\n"
                                "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                 "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.pdf"],
                 "links": [
                     {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                     {
                         "sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                     {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                 ],
                 "inLanguage": "en",
                 "tags": "weather, uk, 2011, temperature, humidity",
                 "price": 10,
                 "type": "dataset"
             },
             "curation": {
                 "rating": 0,
                 "numVotes": 0,
                 "schema": "Binary Votting"
             },
             "additionalInformation": {
                 "updateFrecuency": "yearly"
             },
             "assetId": "001"
             }
json_dict_no_metadata = {"publisherId": "0x2"}
json_dict_no_valid_metadata = {"publisherId": "0x4",
                               "base": {},
                               "assetId": "002"
                               }

json_before = {"publisherId": "0x6",
               "base": {
                   "name": "UK Weather information 2011",
                   "description": "Weather information of UK including temperature and humidity",
                   "size": "3.1gb",
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
                   "tags": "weather, uk, 2011, temperature, humidity",
                   "price": 50,
                   "type": "dataset"
               },
               "curation": {
                   "rating": 0,
                   "numVotes": 0,
                   "schema": "Binary Votting"
               },
               "additionalInformation": {
                   "updateFrecuency": "yearly"
               },
               "assetId": "003"}
json_update = {"publisherId": "0x6",
               "base": {
                   "name": "UK Weather information 2011",
                   "description": "Weather information of UK including temperature and humidity",
                   "size": "3.7gb",
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
                   "tags": "weather, uk, 2011, temperature, humidity",
                   "price": 50,
                   "type": "dataset"
               },
               "curation": {
                   "rating": 0.8,
                   "numVotes": 1,
                   "schema": "Binary Votting"
               },
               "additionalInformation": {
                   "updateFrecuency": "yearly"
               },
               "assetId": "003"}

json_request_consume = {
    'requestId': "",
    'consumerId': "",
    'fixed_msg': "",
    'sigEncJWT': ""
}
