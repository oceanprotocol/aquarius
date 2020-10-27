ddo_event_sample = {
    "@context": "https://w3id.org/did/v1",
    "id": "did:op:ffa5037987b74fbab600d7515605146bb7babcb929c94c60ba93ac5ceda56775",
    "publicKey": [
      {
        "id": "did:op:ffa5037987b74fbab600d7515605146bb7babcb929c94c60ba93ac5ceda56775",
        "type": "EthereumECDSAKey",
        "owner": "0xBE5449a6A97aD46c8558A3356267Ee5D2731ab5e"
      }
    ],
    "authentication": [
      {
        "type": "RsaSignatureAuthentication2018",
        "publicKey": "did:op:ffa5037987b74fbab600d7515605146bb7babcb929c94c60ba93ac5ceda56775"
      }
    ],
    "service": [
      {
        "type": "metadata",
        "attributes": {
          "curation": {
            "rating": 0,
            "numVotes": 0,
            "isListed": True
          },
          "main": {
            "type": "dataset",
            "name": "Event DDO sample",
            "dateCreated": "2020-07-13T09:47:27Z",
            "author": "Met Office",
            "license": "CC-BY",
            "files": [
              {
                "checksum": "efb2c764274b745f5fc37f97c6b0e764",
                "contentLength": "4535431",
                "contentType": "text/csv",
                "encoding": "UTF-8",
                "compression": "zip",
                "index": 0
              }
            ],
            "datePublished": "2020-07-13T09:47:29Z"
          },
          "encryptedFiles": "0x045479dadbdb0ef593998d8f713f2a42585dc7415288326df5737fc3e2a42eee72d50748e820f495ac3abb0a5df99b299984adc2fec2c3883486b87855f739bbd83af73b9ef48726a9c7922badeeb5895ea392c840dccf6b1726de845baad5301087bba0bf447d518a46125b430409050e45a431aea4d3d08bdc97471d18eb0714960045efe65705b4c2670d5ca8e1428f4f53f2d2b11b21719098df8cf013d9aba5c8d1640a09e46a3fb68c87a0c02244caae754a4b6dffcde45e90b4921ae8d2fb84a8f771736860703d797d22ed6405d0cc03a0a5b7c6fab7c8e3ccf30ded364c28ee9a564db01dcdbe93b41a38ffcb0cdc66c43507c4a599e0cfa17561e4af41a6885076a399f41384aabf5c29b587b133b85cb4b879314c969c113d2fd3a552cad771fb752a21d325effe8b8814c603e17e01ff769c40a942c683d46918517a0210112ecd6a25a836d8778414ef24060ab821cbf9ea652a13fa35176fabdd"
        },
        "index": 0
      },
      {
        "type": "compute",
        "index": 1,
        "serviceEndpoint": "http://localhost:8030/api/v1/services/compute",
        "attributes": {
          "main": {
            "name": "dataAssetComputingService",
            "creator": "0xBE5449a6A97aD46c8558A3356267Ee5D2731ab5e",
            "datePublished": "2020-07-13T09:47:27Z",
            "cost": "1000",
            "timeout": 3600,
            "provider": {
              "type": "Azure",
              "description": "Compute service with 16gb ram for each node.",
              "environment": {
                "cluster": {
                  "type": "Kubernetes",
                  "url": "http://10.0.0.17/xxx"
                },
                "supportedServers": [
                  {
                    "image": "tensorflow/tensorflow",
                    "tag": "latest",
                    "checksum": "sha256:cb57ecfa6ebbefd8ffc7f75c0f00e57a7fa739578a429b6f72a0df19315deadc"
                  }
                ],
                "supportedContainers": [
                  {
                    "serverId": "1",
                    "serverType": "xlsize",
                    "cost": "50",
                    "cpu": "16",
                    "gpu": "0",
                    "memory": "128gb",
                    "disk": "160gb",
                    "maxExecutionTime": 86400
                  }
                ]
              }
            },
            "privacy": {
              "allowRawAlgorithm": False,
              "allowNetworkAccess": False,
              "trustedAlgorithms": []
            }
          }
        }
      },
      {
        "type": "access",
        "index": 2,
        "serviceEndpoint": "http://localhost:8030/api/v1/services/consume",
        "attributes": {
          "main": {
            "creator": "0xBE5449a6A97aD46c8558A3356267Ee5D2731ab5e",
            "datePublished": "2020-07-13T09:42:49Z",
            "cost": 10,
            "timeout": 0,
            "name": "dataAssetAccess"
          }
        }
      }
    ],
    "dataToken": "0x20e91598bb797eEd2C7D4431a274c2997D080f53",
    "created": "2020-07-13T09:47:29Z",
    "proof": {
      "created": "2020-07-13T09:47:29Z",
      "creator": "0xBE5449a6A97aD46c8558A3356267Ee5D2731ab5e",
      "type": "DDOIntegritySignature",
      "signatureValue": "0x48fa02b7227d09b2a4ae9d6bab9ed8bfc42b3c5bf105b8eba92f16f39842672e4605387cabdc56b4f42edf57879fb02ab9d4b1d699522d6b15c949b4a7a734f101"
    },
    "updated": "2020-07-13T09:47:29Z",
    "accessWhiteList": ["0x123","0x456"]
  }
