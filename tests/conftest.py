#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import copy
import json

import pytest

from aquarius.constants import BaseURLs
from aquarius.run import app

app = app


@pytest.fixture
def base_ddo_url():
    return BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo'


@pytest.fixture
def client_with_no_data():
    client = app.test_client()
    yield client


@pytest.fixture
def client():
    client = app.test_client()
    client.delete(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo')
    post = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                       data=json.dumps(json_update),
                       content_type='application/json')
    post2 = client.post(BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo',
                        data=json.dumps(json_dict),
                        content_type='application/json')

    yield client

    client.delete(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post.data.decode('utf-8'))['id'])
    client.delete(
        BaseURLs.BASE_AQUARIUS_URL + '/assets/ddo/%s' % json.loads(post2.data.decode('utf-8'))[
            'id'])


json_dict = {
  "@context": "https://w3id.org/did/v1",
  "id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
  "created": "2019-05-22T08:44:27Z",
  "publicKey": [
    {
      "id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
      "type": "EthereumECDSAKey",
      "owner": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e"
    }
  ],
  "authentication": [
    {
      "type": "RsaSignatureAuthentication2018",
      "publicKey": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430"
    }
  ],
  "service": [
    {
      "type": "Authorization",
      "serviceEndpoint": "http://localhost:12001",
      "service": "SecretStore",
      "serviceDefinitionId": "0"
    },
    {
      "type": "Access",
      "serviceEndpoint": "http://localhost:8030/api/v1/brizo/services/consume",
      "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize",
      "serviceDefinitionId": "1",
      "templateId": "0x208aca4B0316C9996F085cbD57E01c11Bc0E7cb1",
      "name": "dataAssetAccessServiceAgreement",
      "creator": "",
      "serviceAgreementTemplate": {
        "contractName": "EscrowAccessSecretStoreTemplate",
        "events": [
          {
            "name": "AgreementCreated",
            "actorType": "consumer",
            "handler": {
              "moduleName": "escrowAccessSecretStoreTemplate",
              "functionName": "fulfillLockRewardCondition",
              "version": "0.1"
            }
          }
        ],
        "fulfillmentOrder": [
          "lockReward.fulfill",
          "accessSecretStore.fulfill",
          "escrowReward.fulfill"
        ],
        "conditionDependency": {
          "lockReward": [],
          "accessSecretStore": [],
          "escrowReward": [
            "lockReward",
            "accessSecretStore"
          ]
        },
        "conditions": [
          {
            "name": "lockReward",
            "timelock": 0,
            "timeout": 0,
            "contractName": "LockRewardCondition",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "lockRewardCondition",
                  "functionName": "fulfillAccessSecretStoreCondition",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_rewardAddress",
                "type": "address",
                "value": "0x2AaC920AA4D10b80db9ed0E4EC04A3ff612F2bc6"
              },
              {
                "name": "_amount",
                "type": "uint256",
                "value": "888000000000000000000000000000000"
              }
            ]
          },
          {
            "name": "accessSecretStore",
            "timelock": 0,
            "timeout": 0,
            "contractName": "AccessSecretStoreCondition",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "accessSecretStore",
                  "functionName": "fulfillEscrowRewardCondition",
                  "version": "0.1"
                }
              },
              {
                "name": "TimedOut",
                "actorType": "consumer",
                "handler": {
                  "moduleName": "accessSecretStore",
                  "functionName": "fulfillEscrowRewardCondition",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_documentId",
                "type": "bytes32",
                "value": "0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430"
              },
              {
                "name": "_grantee",
                "type": "address",
                "value": ""
              }
            ]
          },
          {
            "name": "escrowReward",
            "timelock": 0,
            "timeout": 0,
            "contractName": "EscrowReward",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "escrowRewardCondition",
                  "functionName": "verifyRewardTokens",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_amount",
                "type": "uint256",
                "value": "888000000000000000000000000000000"
              },
              {
                "name": "_receiver",
                "type": "address",
                "value": ""
              },
              {
                "name": "_sender",
                "type": "address",
                "value": ""
              },
              {
                "name": "_lockCondition",
                "type": "bytes32",
                "value": ""
              },
              {
                "name": "_releaseCondition",
                "type": "bytes32",
                "value": ""
              }
            ]
          }
        ]
      }
    },
    {
      "type": "Metadata",
      "serviceEndpoint": "http://localhost:5000/api/v1/aquarius/assets/ddo/did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
      "metadata": {
        "base": {
          "name": "Ocean protocol white paper",
          "type": "dataset",
          "description": "Introduce the main concepts and vision behind ocean protocol",
          "dateCreated": "2012-10-10T17:00:00Z",
          "datePublished": "2012-10-10T17:00:00Z",
          "author": "Ocean Protocol Foundation Ltd.",
          "license": "CC-BY",
          "copyrightHolder": "Ocean Protocol Foundation Ltd.",
          "workExample": "Text PDF",
          "inLanguage": "en",
          "categories": [
            "white-papers"
          ],
          "tags": ["data exchange", "sharing", "curation", "bonding curve"],
          "price": "888000000000000000000000000000000",
          "files": [
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "checksumType": "MD5",
              "contentLength": 4535431,
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 0
            },
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "contentLength": 4535431,
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 1
            },
            {
              "index": 2
            }
          ],
          "links": [
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/"
            }
          ],
          "checksum": "6d78a905bd54d373f71940f8b441bb2ef10758a47dab5b94a94becd688a9e58c",
          "encryptedFiles": "<tests.resources.mocks.secret_store_mock.SecretStoreMock object at 0x7f8146a94710>.0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430!![{\"url\": \"https://testocnfiles.blob.core.windows.net/testfiles/testzkp.pdf\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"checksumType\": \"MD5\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"s3://ocean-test-osmosis-data-plugin-dataseeding-1537375953/data.txt\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"http://ipv4.download.thinkbroadband.com/5MB.zip\"}]!!0"
        },
        "curation": {
          "rating": 0.93,
          "numVotes": 123,
          "schema": "Binary Voting"
        },
        "additionalInformation": {
          "updateFrequency": "yearly",
          "structuredMarkup": [
            {
              "uri": "http://skos.um.es/unescothes/C01194/jsonld",
              "mediaType": "application/ld+json"
            },
            {
              "uri": "http://skos.um.es/unescothes/C01194/turtle",
              "mediaType": "text/turtle"
            }
          ]
        }
      },
      "serviceDefinitionId": "2"
    }
  ],
  "proof": {
    "type": "DDOIntegritySignature",
    "created": "2019-05-22T08:44:27Z",
    "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
    "signatureValue": "0xbd7b46b3ac664167bc70ac211b1a1da0baed9ead91613a5f02dfc25c1bb6e3ff40861b455017e8a587fd4e37b703436072598c3a81ec88be28bfe33b61554a471b"
  }
}
json_dict2 = {
  "@context": "https://w3id.org/did/v1",
  "id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
  "created": "2019-05-22T08:44:27Z",
  "publicKey": [
    {
      "id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
      "type": "EthereumECDSAKey",
      "owner": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e"
    }
  ],
  "authentication": [
    {
      "type": "RsaSignatureAuthentication2018",
      "publicKey": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430"
    }
  ],
  "service": [
    {
      "type": "Authorization",
      "serviceEndpoint": "http://localhost:12001",
      "service": "SecretStore",
      "serviceDefinitionId": "0"
    },
    {
      "type": "Access",
      "serviceEndpoint": "http://localhost:8030/api/v1/brizo/services/consume",
      "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize",
      "serviceDefinitionId": "1",
      "templateId": "0x208aca4B0316C9996F085cbD57E01c11Bc0E7cb1",
      "name": "dataAssetAccessServiceAgreement",
      "creator": "",
      "serviceAgreementTemplate": {
        "contractName": "EscrowAccessSecretStoreTemplate",
        "events": [
          {
            "name": "AgreementCreated",
            "actorType": "consumer",
            "handler": {
              "moduleName": "escrowAccessSecretStoreTemplate",
              "functionName": "fulfillLockRewardCondition",
              "version": "0.1"
            }
          }
        ],
        "fulfillmentOrder": [
          "lockReward.fulfill",
          "accessSecretStore.fulfill",
          "escrowReward.fulfill"
        ],
        "conditionDependency": {
          "lockReward": [],
          "accessSecretStore": [],
          "escrowReward": [
            "lockReward",
            "accessSecretStore"
          ]
        },
        "conditions": [
          {
            "name": "lockReward",
            "timelock": 0,
            "timeout": 0,
            "contractName": "LockRewardCondition",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "lockRewardCondition",
                  "functionName": "fulfillAccessSecretStoreCondition",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_rewardAddress",
                "type": "address",
                "value": "0x2AaC920AA4D10b80db9ed0E4EC04A3ff612F2bc6"
              },
              {
                "name": "_amount",
                "type": "uint256",
                "value": "888000000000000000000000000000000"
              }
            ]
          },
          {
            "name": "accessSecretStore",
            "timelock": 0,
            "timeout": 0,
            "contractName": "AccessSecretStoreCondition",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "accessSecretStore",
                  "functionName": "fulfillEscrowRewardCondition",
                  "version": "0.1"
                }
              },
              {
                "name": "TimedOut",
                "actorType": "consumer",
                "handler": {
                  "moduleName": "accessSecretStore",
                  "functionName": "fulfillEscrowRewardCondition",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_documentId",
                "type": "bytes32",
                "value": "0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430"
              },
              {
                "name": "_grantee",
                "type": "address",
                "value": ""
              }
            ]
          },
          {
            "name": "escrowReward",
            "timelock": 0,
            "timeout": 0,
            "contractName": "EscrowReward",
            "functionName": "fulfill",
            "events": [
              {
                "name": "Fulfilled",
                "actorType": "publisher",
                "handler": {
                  "moduleName": "escrowRewardCondition",
                  "functionName": "verifyRewardTokens",
                  "version": "0.1"
                }
              }
            ],
            "parameters": [
              {
                "name": "_amount",
                "type": "uint256",
                "value": "888000000000000000000000000000000"
              },
              {
                "name": "_receiver",
                "type": "address",
                "value": ""
              },
              {
                "name": "_sender",
                "type": "address",
                "value": ""
              },
              {
                "name": "_lockCondition",
                "type": "bytes32",
                "value": ""
              },
              {
                "name": "_releaseCondition",
                "type": "bytes32",
                "value": ""
              }
            ]
          }
        ]
      }
    },
    {
      "type": "Metadata",
      "serviceEndpoint": "http://localhost:5000/api/v1/aquarius/assets/ddo/did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
      "metadata": {
        "base": {
          "name": "Ocean protocol white paper",
          "type": "dataset",
          "description": "Introduce the main concepts and vision behind ocean protocol",
          "dateCreated": "2012-10-10T17:00:00Z",
          "datePublished": "2012-10-10T17:00:00Z",
          "author": "Ocean Protocol Foundation Ltd.",
          "license": "CC-BY",
          "copyrightHolder": "Ocean Protocol Foundation Ltd.",
          "workExample": "Text PDF",
          "inLanguage": "en",
          "categories": [
            "white-papers"
          ],
          "tags": ["data exchange", "sharing", "curation", "bonding curve"],
          "price": "888000000000000000000000000000000",
          "files": [
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "checksumType": "MD5",
              "contentLength": 4535431,
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 0
            },
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "contentLength": 4535431,
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 1
            },
            {
              "index": 2
            }
          ],
          "links": [
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/"
            }
          ],
          "checksum": "6d78a905bd54d373f71940f8b441bb2ef10758a47dab5b94a94becd688a9e58c",
          "encryptedFiles": "<tests.resources.mocks.secret_store_mock.SecretStoreMock object at 0x7f8146a94710>.0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430!![{\"url\": \"https://testocnfiles.blob.core.windows.net/testfiles/testzkp.pdf\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"checksumType\": \"MD5\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"s3://ocean-test-osmosis-data-plugin-dataseeding-1537375953/data.txt\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"http://ipv4.download.thinkbroadband.com/5MB.zip\"}]!!0"
        },
        "curation": {
          "rating": 0.93,
          "numVotes": 123,
          "schema": "Binary Voting",
          "isListed": False
        },
        "additionalInformation": {
          "updateFrequency": "yearly",
          "structuredMarkup": [
            {
              "uri": "http://skos.um.es/unescothes/C01194/jsonld",
              "mediaType": "application/ld+json"
            },
            {
              "uri": "http://skos.um.es/unescothes/C01194/turtle",
              "mediaType": "text/turtle"
            }
          ]
        }
      },
      "serviceDefinitionId": "2"
    }
  ],
  "proof": {
    "type": "DDOIntegritySignature",
    "created": "2019-05-22T08:44:27Z",
    "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
    "signatureValue": "0xbd7b46b3ac664167bc70ac211b1a1da0baed9ead91613a5f02dfc25c1bb6e3ff40861b455017e8a587fd4e37b703436072598c3a81ec88be28bfe33b61554a471b"
  }
}
json_dict_no_metadata = {"publisherId": "0x2"}
json_dict_no_valid_metadata = {"publisherId": "0x4",
                               "base": {},
                               "assetId": "002"
                               }

json_before = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "id": "did:op:112233445566778899",
    "publicKey": [
        {
            "id": "did:op:123456789abcdefghi#keys-1",
            "type": "RsaVerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        },
        {
            "id": "did:op:123456789abcdefghi#keys-2",
            "type": "Ed25519VerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        }
    ],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-1"
        },
        {
            "type": "ieee2410Authentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-2"
        }
    ],
    "proof": {
        "type": "UUIDSignature",
        "created": "2016-02-08T16:02:20Z",
        "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
        "signatureValue": "QNB13Y7Q9...1tzjn4w=="
    },
    "service": [
        {
            "type": "Consume",
            "serviceDefinitionId": "0",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}"
        },
        {
            "type": "Compute",
            "serviceDefinitionId": "1",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
        },
        {
            "type": "Metadata",
            "serviceDefinitionId": "2",
            "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
            "metadata": {
                "base": {
                    "name": "UK Weather information 2011",
                    "type": "dataset",
                    "description": "Weather information of UK including temperature and humidity",
                    "dateCreated": "2012-10-10T17:00:00Z",
                    "datePublished": "2012-10-10T17:00:00Z",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity /n 423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "index": 0,
                        "contentLength": 4535431,
                        "contentType": "text/csv",
                        "encoding": "UTF-8",
                        "compression": "zip",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                    }
                    ],
                    "encryptedFiles": "0xkasdhfkljhasdfkjasdhf",
                    "links": [
                        {
                            "name": "Sample of Asset Data",
                            "type": "sample",
                            "url": "https://foo.com/sample.csv"
                        },
                        {
                            "name": "Data Format Definition",
                            "type": "format",
                            "url": "https://foo.com/sample2.csv"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": ["weather", "uk", "2011", "temperature", "humidity"],
                    "price": "88888880000000000000",
                    "checksum": "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85262"
                },
                "curation": {
                    "rating": 0.0,
                    "numVotes": 0,
                    "schema": "Binary Votting",
                    "isListed": True
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly",
                    "structuredMarkup": [
                        {"uri": "http://skos.um.es/unescothes/C01194/jsonld",
                         "mediaType": "application/ld+json"},
                        {"uri": "http://skos.um.es/unescothes/C01194/turtle",
                         "mediaType": "text/turtle"}]
                }
            }
        }
    ]
}
json_update = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "id": "did:op:112233445566778899",
    "publicKey": [
        {
            "id": "did:op:123456789abcdefghi#keys-1",
            "type": "RsaVerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        },
        {
            "id": "did:op:123456789abcdefghi#keys-2",
            "type": "Ed25519VerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        }
    ],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-1"
        },
        {
            "type": "ieee2410Authentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-2"
        }
    ],
    "proof": {
        "type": "UUIDSignature",
        "created": "2016-02-08T16:02:20Z",
        "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
        "signatureValue": "QNB13Y7Q9...1tzjn4w=="
    },
    "service": [
        {
            "type": "Consume",
            "serviceDefinitionId": "0",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}"
        },
        {
            "type": "Compute",
            "serviceDefinitionId": "1",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
        },
        {
            "type": "Metadata",
            "serviceDefinitionId": "2",
            "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
            "metadata": {
                "base": {
                    "name": "UK Weather information 2012",
                    "type": "dataset",
                    "description": "Weather information of UK including temperature and humidity and white",
                    "dateCreated": "2012-02-01T10:55:11Z",
                    "datePublished": "2012-02-01T10:55:11Z",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity /n 423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "index": 0,
                        "contentLength": 4535431,
                        "contentType": "text/csv",
                        "encoding": "UTF-8",
                        "compression": "zip",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                    }
                    ],
                    "encryptedFiles": "0xkasdhfkljhasdfkjasdhf",
                    "links": [
                        {
                            "name": "Sample of Asset Data",
                            "type": "sample",
                            "url": "https://foo.com/sample.csv"
                        },
                        {
                            "name": "Data Format Definition",
                            "type": "format",
                            "url": "https://foo.com/sample2.csv"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": ["weather", "uk", "2011", "temperature", "humidity"],
                    "price": "15",
                    "checksum": "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85264"
                },
                "curation": {
                    "rating": 8.0,
                    "numVotes": 1,
                    "schema": "Binary Votting",
                    "isListed": True
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly",
                    "structuredMarkup": [
                        {"uri": "http://skos.um.es/unescothes/C01194/jsonld",
                         "mediaType": "application/ld+json"},
                        {"uri": "http://skos.um.es/unescothes/C01194/turtle",
                         "mediaType": "text/turtle"}]
                }
            }
        }
    ]
}
json_valid = {
  "base": {
    "name": "10 Monkey Species Small",
    "dateCreated": "2012-02-01T10:55:11Z",
    "author": "Mario",
    "license": "CC0: Public Domain",
    "price": "10",
    "files": [
      {
        "index": 0,
        "contentType": "application/zip",
        "encoding": "UTF-8",
        "compression": "zip",
        "checksum": "2bf9d229d110d1976cdf85e9f3256c7f",
        "checksumType": "MD5",
        "contentLength": 12057507,
        "url": "https://s3.amazonaws.com/assets/training.zip"
      },
      {
        "index": 1,
        "contentType": "text/txt",
        "encoding": "UTF-8",
        "compression": "none",
        "checksum": "354d19c0733c47ef3a6cce5b633116b0",
        "checksumType": "MD5",
        "contentLength": 928,
        "url": "https://s3.amazonaws.com/datacommons/monkey_labels.txt"
      },
      {
        "index": 2,
        "contentType": "application/zip",
        "url": "https://s3.amazonaws.com/datacommons/validation.zip"
      }
    ],
    "checksum": "",
    "categories": [
      "image"
    ],
    "tags": [
      "image data",
      "classification",
      "animals"
    ],
    "type": "dataset",
    "description": "EXAMPLE ONLY ",
    "copyrightHolder": "Unknown",
    "workExample": "image path, id, label",
    "links": [
      {
        "name": "example model",
        "url": "https://drive.google.com/open?id=1uuz50RGiAW8YxRcWeQVgQglZpyAebgSM"
      },
      {
        "name": "example code",
        "type": "example code",
        "url": "https://github.com/slothkong/CNN_classification_10_monkey_species"
      },
      {
        "url": "https://s3.amazonaws.com/datacommons/links/discovery/n5151.jpg",
        "name": "n5151.jpg",
        "type": "discovery"
      },
      {
        "url": "https://s3.amazonaws.com/datacommons/links/sample/sample.zip",
        "name": "sample.zip",
        "type": "sample"
      }
    ],
    "inLanguage": "en"
  }
}


test_assets = []
for i in range(10):
    a = copy.deepcopy(json_dict)
    a['id'] = a['id'][:-2] + str(i) +str(i)
    test_assets.append(a)

json_request_consume = {
    'requestId': "",
    'consumerId': "",
    'fixed_msg': "",
    'sigEncJWT': ""
}
