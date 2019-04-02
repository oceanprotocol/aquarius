#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import pytest

from aquarius.run import app

app = app


@pytest.fixture
def client():
    client = app.test_client()
    yield client


json_dict = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "id": "did:op:123456789abcdefghi",
    "publicKey": [
        {
            "id": "did:op:123456789abcdefghi#keys-1",
            "type": "RsaVerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        }, {
            "id": "did:op:123456789abcdefghi#keys-2",
            "type": "Ed25519VerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        }, {
            "id": "did:op:123456789abcdefghi#keys-3",
            "type": "RsaPublicKeyExchangeKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        }],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-1"
        },
        {
            "type": "ieee2410Authentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-2"
        }],
    "proof": {
        "type": "UUIDSignature",
        "created": "2016-02-08T16:02:20Z",
        "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
        "signatureValue": "QNB13Y7Q9...1tzjn4w=="
    },
    "service": [
        {
            "type": "Access",
            "serviceDefinitionId": "0",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}",
            "purchaseEndpoint": "http://mybrizo.org/api/v1/brizo/services/access/purchase?",
            "templateId": "044852b2a670ade5407e78fb2863c51000000000000000000000000000000000",
            "encryption": {
                "type": "SecretStore",
                "url": "http://secretstore.org:12001"
            },
            "serviceAgreementContract": {
                "contractName": "ServiceAgreement",
                "fulfillmentOperator": 1,
                "events": [{
                    "name": "ExecuteAgreement",
                    "actorType": "consumer",
                    "handler": {
                        "moduleName": "payment",
                        "functionName": "lockPayment",
                        "version": "0.1"
                    }
                }]
            },
            "conditions": [
                {
                    "name": "lockPayment",
                    "dependencies": [],
                    "timeout": 0,
                    "isTerminalCondition": 0,
                    "conditionKey":
                        "0x313d20f9cda19e1f5702af79e5ebfa7cb434918722f9b334000ea71cdaac1614",
                    "contractName": "PaymentConditions",
                    "functionName": "lockPayment",
                    "index": 0,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint256",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentLocked",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "accessControl",
                            "functionName": "grantAccess",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "grantAccess",
                    "dependencies": [{
                        "name": "lockPayment",
                        "timeout": 0
                    }
                    ],
                    "timeout": 0,
                    "isTerminalCondition": 0,
                    "conditionKey":
                        "0x38163b4835d3b0c780fcdf6a872e3e86f84393a0bda8e8b642df39a8d05c4c1a",
                    "contractName": "AccessConditions",
                    "functionName": "grantAccess",
                    "index": 1,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "documentKeyId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }
                    ],
                    "events": [{
                        "name": "AccessGranted",
                        "actorType": "consumer",
                        "handler": {
                            "moduleName": "asset",
                            "functionName": "consumeService",
                            "version": "0.1"
                        }
                    }, {
                        "name": "AccessGranted",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "payment",
                            "functionName": "releasePayment",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "releasePayment",
                    "dependencies": [{
                        "name": "grantAccess",
                        "timeout": 0
                    }
                    ],
                    "timeout": 0,
                    "isTerminalCondition": 1,
                    "conditionKey":
                        "0x477f516713f4b0de54d0e0f4429f593c63f2dd2ca4789633e02a446c7978f3cb",
                    "contractName": "PaymentConditions",
                    "functionName": "releasePayment",
                    "index": 2,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentReleased",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "serviceAgreement",
                            "functionName": "fulfillAgreement",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "refundPayment",
                    "dependencies": [{
                        "name": "lockPayment",
                        "timeout": 0
                    }, {
                        "name": "grantAccess",
                        "timeout": 86400
                    }
                    ],
                    "timeout": 1,
                    "isTerminalCondition": 1,
                    "conditionKey":
                        "0x385d3af26f7c057688a4988fb784c392a97ce472a4feb4435968fed04809e8dc",
                    "contractName": "PaymentConditions",
                    "functionName": "refundPayment",
                    "index": 3,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentRefund",
                        "actorType": "consumer",
                        "handler": {
                            "moduleName": "serviceAgreement",
                            "functionName": "fulfillAgreement",
                            "version": "0.1"
                        }
                    }]
                }
            ]

        },
        {
            "type": "CloudCompute",
            "serviceDefinitionId": "1",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}",
            "templateId": "044852b2a670ade5407e78fb2863c51000000000000000000000000000000002"

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
                    "size": "3.1gb",
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "encoding": "UTF-8",
                    "compression": "zip",
                    "contentType": "text/csv",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity\n423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "contentLength": "4535431",
                        "contentType": "text/csv",
                        "encoding": "UTF-8",
                        "compression": "zip",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
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
                            "AssetID":
                                "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity",
                    "price": 10,
                    "checksum": "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85262"
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly",
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
            }
        }
    ]
}
json_dict2 = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "id": "did:op:123456789abcdefghi",
    "publicKey": [
        {
            "id": "did:op:123456789abcdefghi#keys-1",
            "type": "RsaVerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        }, {
            "id": "did:op:123456789abcdefghi#keys-2",
            "type": "Ed25519VerificationKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
        }, {
            "id": "did:op:123456789abcdefghi#keys-3",
            "type": "RsaPublicKeyExchangeKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
        }],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-1"
        },
        {
            "type": "ieee2410Authentication2018",
            "publicKey": "did:op:123456789abcdefghi#keys-2"
        }],
    "proof": {
        "type": "UUIDSignature",
        "created": "2016-02-08T16:02:20Z",
        "creator": "did:example:8uQhQMGzWxR8vw5P3UWH1ja",
        "signatureValue": "QNB13Y7Q9...1tzjn4w=="
    },
    "service": [
        {
            "type": "Access",
            "serviceDefinitionId": "0",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}",
            "purchaseEndpoint": "http://mybrizo.org/api/v1/brizo/services/access/purchase?",
            "templateId": "044852b2a670ade5407e78fb2863c51000000000000000000000000000000000",
            "encryption": {
                "type": "SecretStore",
                "url": "http://secretstore.org:12001"
            },
            "serviceAgreementContract": {
                "contractName": "ServiceAgreement",
                "fulfillmentOperator": 1,
                "events": [{
                    "name": "ExecuteAgreement",
                    "actorType": "consumer",
                    "handler": {
                        "moduleName": "payment",
                        "functionName": "lockPayment",
                        "version": "0.1"
                    }
                }]
            },
            "conditions": [
                {
                    "name": "lockPayment",
                    "dependencies": [],
                    "timeout": 0,
                    "isTerminalCondition": 0,
                    "conditionKey":
                        "0x313d20f9cda19e1f5702af79e5ebfa7cb434918722f9b334000ea71cdaac1614",
                    "contractName": "PaymentConditions",
                    "functionName": "lockPayment",
                    "index": 0,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint256",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentLocked",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "accessControl",
                            "functionName": "grantAccess",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "grantAccess",
                    "dependencies": [{
                        "name": "lockPayment",
                        "timeout": 0
                    }
                    ],
                    "timeout": 0,
                    "isTerminalCondition": 0,
                    "conditionKey":
                        "0x38163b4835d3b0c780fcdf6a872e3e86f84393a0bda8e8b642df39a8d05c4c1a",
                    "contractName": "AccessConditions",
                    "functionName": "grantAccess",
                    "index": 1,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "documentKeyId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }
                    ],
                    "events": [{
                        "name": "AccessGranted",
                        "actorType": "consumer",
                        "handler": {
                            "moduleName": "asset",
                            "functionName": "consumeService",
                            "version": "0.1"
                        }
                    }, {
                        "name": "AccessGranted",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "payment",
                            "functionName": "releasePayment",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "releasePayment",
                    "dependencies": [{
                        "name": "grantAccess",
                        "timeout": 0
                    }
                    ],
                    "timeout": 0,
                    "isTerminalCondition": 1,
                    "conditionKey":
                        "0x477f516713f4b0de54d0e0f4429f593c63f2dd2ca4789633e02a446c7978f3cb",
                    "contractName": "PaymentConditions",
                    "functionName": "releasePayment",
                    "index": 2,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentReleased",
                        "actorType": "publisher",
                        "handler": {
                            "moduleName": "serviceAgreement",
                            "functionName": "fulfillAgreement",
                            "version": "0.1"
                        }
                    }]
                }, {
                    "name": "refundPayment",
                    "dependencies": [{
                        "name": "lockPayment",
                        "timeout": 0
                    }, {
                        "name": "grantAccess",
                        "timeout": 86400
                    }
                    ],
                    "timeout": 1,
                    "isTerminalCondition": 1,
                    "conditionKey":
                        "0x385d3af26f7c057688a4988fb784c392a97ce472a4feb4435968fed04809e8dc",
                    "contractName": "PaymentConditions",
                    "functionName": "refundPayment",
                    "index": 3,
                    "parameters": [
                        {
                            "name": "assetId",
                            "type": "bytes32",
                            "value":
                                "08a429b8529856d59867503f8056903a680935a76950bb9649785cc97869a43d"
                        }, {
                            "name": "price",
                            "type": "uint",
                            "value": "10"
                        }
                    ],
                    "events": [{
                        "name": "PaymentRefund",
                        "actorType": "consumer",
                        "handler": {
                            "moduleName": "serviceAgreement",
                            "functionName": "fulfillAgreement",
                            "version": "0.1"
                        }
                    }]
                }
            ]

        },
        {
            "type": "CloudCompute",
            "serviceDefinitionId": "1",
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}",
            "templateId": "044852b2a670ade5407e78fb2863c51000000000000000000000000000000002"

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
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "compression": "zip",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity\n423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "contentLength": "4535431",
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
                            "AssetID":
                                "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity",
                    "price": 10,
                    "checksum": "38803b9e6f04fce3fba4b124524672592264d31847182c689095a081c9e85262"
                },
                "curation": {
                    "rating": 0.93,
                    "numVotes": 123,
                    "schema": "Binary Voting",
                    "isListed": False
                },
                "additionalInformation": {
                    "updateFrecuency": "yearly",
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
            }
        }
    ]
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
                    "size": "3.1gb",
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "encoding": "UTF-8",
                    "compression": "zip",
                    "contentType": "text/csv",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity\n423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "contentLength": "4535431",
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
                            "AssetID":
                                "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity",
                    "price": 10,
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
                    "description": "Weather information of UK including temperature and humidity",
                    "size": "3.1gb",
                    "dateCreated": "2012-02-01T10:55:11+00:00",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "copyrightHolder": "Met Office",
                    "encoding": "UTF-8",
                    "compression": "zip",
                    "contentType": "text/csv",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity\n423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "files": [{
                        "contentLength": "4535431",
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
                            "AssetID":
                                "4d517500da0acb0d65a716f61330969334630363ce4a6a9d39691026ac7908ea"
                        }
                    ],
                    "inLanguage": "en",
                    "tags": "weather, uk, 2011, temperature, humidity",
                    "price": 15,
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
    "price": 10,
    "files": [
      {
        "contentType": "application/zip",
        "encoding": "UTF-8",
        "compression": "zip",
        "checksum": "2bf9d229d110d1976cdf85e9f3256c7f",
        "checksumType": "MD5",
        "contentLength": 12057507,
        "url": "https://s3.amazonaws.com/assets/training.zip"
      },
      {
        "contentType": "text/txt",
        "encoding": "UTF-8",
        "compression": "none",
        "checksum": "354d19c0733c47ef3a6cce5b633116b0",
        "checksumType": "MD5",
        "contentLength": 928,
        "url": "https://s3.amazonaws.com/datacommons/monkey_labels.txt"
      },
      {
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


json_request_consume = {
    'requestId': "",
    'consumerId': "",
    'fixed_msg': "",
    'sigEncJWT': ""
}
