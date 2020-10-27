json_before = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "dataToken": "0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687",
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
            "attributes": {
                "main": {
                    "cost":"10",
                    "timeout":"0"
                }
            },
            "type": "access",
            "index": 0,
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}"
        },
        {
            "attributes": {
                "main": {
                    "cost":"10",
                    "timeout":"0",
                    "name": "dataAssetComputingServiceAgreement"
                }
            },
            "type": "compute",
            "index": 1,
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
            
        },
        {
            "type": "metadata",
            "index": 2,
            "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
            "attributes": {
                "main": {
                    "name": "UK Weather information 2011",
                    "type": "dataset",
                    "dateCreated": "2012-10-10T17:00:00Z",
                    "datePublished": "2012-10-10T17:00:00Z",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "files": [{
                        "index": 0,
                        "contentLength": "4535431",
                        "contentType": "text/csv",
                        "encoding": "UTF-8",
                        "compression": "zip",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                    }
                    ]
                },
                "encryptedFiles": "0xkasdhfkljhasdfkjasdhf",
                "curation": {
                    "rating": 0.0,
                    "numVotes": 0,
                    "schema": "Binary Votting",
                    "isListed": True
                },
                "additionalInformation": {
                    "description": "Weather information of UK including temperature and humidity",
                    "copyrightHolder": "Met Office",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity /n 423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "inLanguage": "en",
                    "tags": ["weather", "uk", "2011", "temperature", "humidity"],
                    "updateFrequency": "yearly",
                    "structuredMarkup": [
                        {"uri": "http://skos.um.es/unescothes/C01194/jsonld",
                         "mediaType": "application/ld+json"},
                        {"uri": "http://skos.um.es/unescothes/C01194/turtle",
                         "mediaType": "text/turtle"}
                    ],
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
                    ]

                }
            }
        }
    ]
}
json_update = {
    "@context": "https://w3id.org/future-method/v1",
    "created": "2016-02-08T16:02:20Z",
    "dataToken": "0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687",
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
            "attributes": {
                "main": {
                    "cost":"10",
                    "timeout":"0"              
                }
            },
            "type": "access",
            "index": 0,
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${"
                               "pubKey}&serviceId={serviceId}&url={url}"
        },
        {
            "type": "compute",
            "index": 1,
            "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${"
                               "pubKey}&serviceId={serviceId}&algo={algo}&container={container}",
            "attributes": {
                "main": {
                    "cost":"5",
                    "timeout":"0",
                    "name": "dataAssetComputingServiceAgreement"
                }
            }
        },
        {
            "type": "metadata",
            "index": 2,
            "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
            "attributes": {
                "main": {
                    "name": "UK Weather information 2012",
                    "type": "dataset",
                    "dateCreated": "2012-02-01T10:55:11Z",
                    "datePublished": "2012-02-01T10:55:11Z",
                    "author": "Met Office",
                    "license": "CC-BY",
                    "files": [{
                        "index": 0,
                        "contentLength": "4535431",
                        "contentType": "text/csv",
                        "encoding": "UTF-8",
                        "compression": "zip",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932"
                    }]
                },
                "encryptedFiles": "0xkasdhfkljhasdfkjasdhf",
                "curation": {
                    "rating": 8.0,
                    "numVotes": 1,
                    "schema": "Binary Votting",
                    "isListed": True
                },
                "additionalInformation": {
                    "description": "Weather information of UK including temperature and humidity and white",
                    "copyrightHolder": "Met Office",
                    "workExample": "stationId,latitude,longitude,datetime,temperature,"
                                   "humidity /n 423432fsd,51.509865,-0.118092,"
                                   "2011-01-01T10:55:11+00:00,7.2,68",
                    "inLanguage": "en",
                    "tags": ["weather", "uk", "2011", "temperature", "humidity"],
                    "updateFrecuency": "yearly",
                    "structuredMarkup": [
                        {"uri": "http://skos.um.es/unescothes/C01194/jsonld",
                         "mediaType": "application/ld+json"},
                        {"uri": "http://skos.um.es/unescothes/C01194/turtle",
                         "mediaType": "text/turtle"}
                    ],
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
                    ]
                }
            }
        }
    ]
}
json_valid = {
    "main": {
        "name": "10 Monkey Species Small",
        "dateCreated": "2012-02-01T10:55:11Z",
        "author": "Mario",
        "license": "CC0: Public Domain",
        "files": [
            {
                "index": 0,
                "contentType": "application/zip",
                "encoding": "UTF-8",
                "compression": "zip",
                "checksum": "2bf9d229d110d1976cdf85e9f3256c7f",
                "checksumType": "MD5",
                "contentLength": "12057507",
                "url": "https://s3.amazonaws.com/assets/training.zip"
            },
            {
                "index": 1,
                "contentType": "text/txt",
                "encoding": "UTF-8",
                "compression": "none",
                "checksum": "354d19c0733c47ef3a6cce5b633116b0",
                "checksumType": "MD5",
                "contentLength": "928",
                "url": "https://s3.amazonaws.com/datacommons/monkey_labels.txt"
            },
            {
                "index": 2,
                "contentType": "application/zip",
                "url": "https://s3.amazonaws.com/datacommons/validation.zip"
            }
        ],
        "type": "dataset",
    },
    "additionalInformation": {
        "description": "EXAMPLE ONLY ",
        "categories": [
            "image"
        ],
        "tags": [
            "image data",
            "classification",
            "animals"
        ],
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
        "copyrightHolder": "Unknown",
        "inLanguage": "en"
    }
}
