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
      "type": "authorization",
      "serviceEndpoint": "http://localhost:12001",
      "service": "SecretStore",
      "index": 0
    },
    {
      "type": "access",
      "serviceEndpoint": "http://localhost:8030/api/v1/brizo/services/consume",
      "purchaseEndpoint": "http://localhost:8030/api/v1/brizo/services/access/initialize",
      "index": 1,
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
      "type": "metadata",
      "serviceEndpoint": "http://localhost:5000/api/v1/aquarius/assets/ddo/did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
      "attributes": {
        "main": {
          "name": "Ocean protocol white paper",
          "type": "dataset",
          "dateCreated": "2012-10-10T17:00:00Z",
          "datePublished": "2012-10-10T17:00:00Z",
          "author": "Ocean Protocol Foundation Ltd.",
          "license": "CC-BY",
          "price": "888000000000000000000000000000000",
          "files": [
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "contentType": "text/csv",
              "checksumType": "MD5",
              "contentLength": "4535431",
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 0
            },
            {
              "checksum": "efb2c764274b745f5fc37f97c6b0e761",
              "contentType": "text/csv",

              "contentLength": "4535431",
              "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
              "index": 1
            },
            {
              "index": 2,
              "contentType": "text/csv",

            }
          ]
        },
        "encryptedFiles": "<tests.resources.mocks.secret_store_mock.SecretStoreMock object at 0x7f8146a94710>.0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430!![{\"url\": \"https://testocnfiles.blob.core.windows.net/testfiles/testzkp.pdf\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"checksumType\": \"MD5\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"s3://ocean-test-osmosis-data-plugin-dataseeding-1537375953/data.txt\", \"checksum\": \"efb2c764274b745f5fc37f97c6b0e761\", \"contentLength\": \"4535431\", \"resourceId\": \"access-log2018-02-13-15-17-29-18386C502CAEA932\"}, {\"url\": \"http://ipv4.download.thinkbroadband.com/5MB.zip\"}]!!0",
        "curation": {
          "rating": 0.93,
          "numVotes": 123,
          "schema": "Binary Voting"
        },
        "additionalInformation": {
          "description": "Introduce the main concepts and vision behind ocean protocol",
          "copyrightHolder": "Ocean Protocol Foundation Ltd.",
          "workExample": "Text PDF",
          "inLanguage": "en",
          "categories": [
            "white-papers"
          ],
          "tags": ["data exchange", "sharing", "curation", "bonding curve"],
          "links": [
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs"
                     "-daily/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs"
                     "-averages-25km/"
            },
            {
              "url": "http://data.ceda.ac.uk/badc/ukcp09/"
            }
          ],
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
      "index": 2
    }
  ],
  "proof": {
    "type": "DDOIntegritySignature",
    "created": "2019-05-22T08:44:27Z",
    "creator": "0x00Bd138aBD70e2F00903268F3Db08f2D25677C9e",
    "signatureValue": "0xbd7b46b3ac664167bc70ac211b1a1da0baed9ead91613a5f02dfc25c1bb6e3ff40861b455017e8a587fd4e37b703436072598c3a81ec88be28bfe33b61554a471b"
  }
}
