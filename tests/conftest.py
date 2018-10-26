import pytest

from aquarius.run import app

app = app


@pytest.fixture
def client():
    client = app.test_client()
    yield client


json_dict = {
    "@context": "https://w3id.org/future-method/v1",
    "id": "did:op:123456789abcdefghi",

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
        },
        {
            "id": "did:op:123456789abcdefghi#keys-3896708970",
            "type": "RsaPublicKeyExchangeKey2018",
            "owner": "did:op:123456789abcdefghi",
            "publicKeyPem": "-----BEGIN PUBLIC KEY...END PUBLIC KEY-----\r\n"
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

    "service": [
        {
        "type": "Consume",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"
    },
        {
        "type": "Compute",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
    },
        {
        "type": "Metadata",
        "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
        "metadata": {
            "base": {
                "name": "UK Weather information 2011",
                "type": "dataset",
                "description": "Weather information of UK including temperature and humidity",
                "size": "3.1gb",
                "dateCreated": "2012-10-10T17:00:000Z",
                "author": "Met Office",
                "license": "CC-BY",
                "copyrightHolder": "Met Office",
                "encoding": "UTF-8",
                "compression": "zip",
                "contentType": "text/csv",
                "workExample": "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                "links": [
                    {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                    {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                    {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                ],
                "inLanguage": "en",
                "tags": "weather, uk, 2011, temperature, humidity",
                "price": 10
            },
            "curation": {
                "rating": 0.93,
                "numVotes": 123,
                "schema": "Binary Votting"
            },
            "additionalInformation": {
                "updateFrecuency": "yearly",
                "structuredMarkup": [
                    {"uri": "http://skos.um.es/unescothes/C01194/jsonld", "mediaType": "application/ld+json"},
                    {"uri": "http://skos.um.es/unescothes/C01194/turtle", "mediaType": "text/turtle"}]
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

    "service": [
        {
        "type": "Consume",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"
    },
        {
        "type": "Compute",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
    },
        {
        "type": "Metadata",
        "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
        "metadata": {
            "base": {
                "name": "UK Weather information 2011",
                "type": "dataset",
                "description": "Weather information of UK including temperature and humidity",
                "size": "3.1gb",
                "dateCreated": "2012-10-10T17:00:000Z",
                "author": "Met Office",
                "license": "CC-BY",
                "copyrightHolder": "Met Office",
                "encoding": "UTF-8",
                "compression": "zip",
                "contentType": "text/csv",
                "workExample": "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                "links": [
                    {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                    {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                    {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                ],
                "inLanguage": "en",
                "tags": "weather, uk, 2011, temperature, humidity",
                "price": 10
            },
            "curation": {
                "rating": 0.0,
                "numVotes": 0,
                "schema": "Binary Votting"
            },
            "additionalInformation": {
                "updateFrecuency": "yearly",
                "structuredMarkup": [
                    {"uri": "http://skos.um.es/unescothes/C01194/jsonld", "mediaType": "application/ld+json"},
                    {"uri": "http://skos.um.es/unescothes/C01194/turtle", "mediaType": "text/turtle"}]
            }
        }
    }
    ]
}
json_update = {
    "@context": "https://w3id.org/future-method/v1",
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

    "service": [
        {
        "type": "Consume",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"
    },
        {
        "type": "Compute",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
    },
        {
        "type": "Metadata",
        "serviceEndpoint": "http://myaquarius.org/api/v1/provider/assets/metadata/{did}",
        "metadata": {
            "base": {
                "name": "UK Weather information 2011",
                "type": "dataset",
                "description": "Weather information of UK including temperature and humidity",
                "size": "3.1gb",
                "dateCreated": "2012-10-10T17:00:000Z",
                "author": "Met Office",
                "license": "CC-BY",
                "copyrightHolder": "Met Office",
                "encoding": "UTF-8",
                "compression": "zip",
                "contentType": "text/pdf",
                "workExample": "423432fsd,51.509865,-0.118092,2011-01-01T10:55:11+00:00,7.2,68",
                "contentUrls": ["https://testocnfiles.blob.core.windows.net/testfiles/testzkp.zip"],
                "links": [
                    {"sample1": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/"},
                    {"sample2": "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"},
                    {"fieldsDescription": "http://data.ceda.ac.uk/badc/ukcp09/"}
                ],
                "inLanguage": "en",
                "tags": "weather, uk, 2011, temperature, humidity",
                "price": 10
            },
            "curation": {
                "rating": 8.0,
                "numVotes": 1,
                "schema": "Binary Votting"
            },
            "additionalInformation": {
                "updateFrecuency": "yearly",
                "structuredMarkup": [
                    {"uri": "http://skos.um.es/unescothes/C01194/jsonld", "mediaType": "application/ld+json"},
                    {"uri": "http://skos.um.es/unescothes/C01194/turtle", "mediaType": "text/turtle"}]
            }
        }
    }
    ]
}

json_request_consume = {
    'requestId': "",
    'consumerId': "",
    'fixed_msg': "",
    'sigEncJWT': ""
}
