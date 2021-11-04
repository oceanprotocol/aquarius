#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
algorithm_ddo_sample = {
    "@context": ["https://w3id.org/did/v1"],
    "id": "did:op:0bc278fee025464f8012b811d1bce8e22094d0984e4e49139df5d5ff7a028bdf",
    "created": "2019-02-08T08:13:49Z",
    "updated": "2019-02-08T08:13:49Z",
    "version": "v4.0.0",
    "proof": {
        "created": "2019-02-08T08:13:41Z",
        "creator": "0x37BB53e3d293494DE59fBe1FF78500423dcFd43B",
        "signatureValue": "did:op:0bc278fee025464f8012b811d1bce8e22094d0984e4e49139df5d5ff7a028bdf",
        "type": "DDOIntegritySignature",
        "checksum": {
            "0": "0x52b5c93b82dd9e7ecc3d9fdf4755f7f69a54484941897dc517b4adfe3bbc3377",
            "1": "0x999999952b5c93b82dd9e7ecc3d9fdf4755f7f69a54484941897dc517b4adfe3",
        },
    },
    "metadata": {
        "author": "John Doe",
        "license": "CC-BY",
        "name": "My super algorithm",
        "type": "algorithm",
        "description": "workflow for weather",
        "algorithm": {
            "language": "scala",
            "format": "docker-image",
            "version": "0.1",
            "container": {
                "entrypoint": "node $ALGO",
                "image": "node",
                "tag": "10",
                "checksum": "test",
            },
        },
        "additionalInformation": {
            "description": "Workflow to aggregate weather information",
            "tags": ["weather", "uk", "2011", "workflow", "aggregation"],
            "copyrightHolder": "John Doe",
        },
    },
    "services": [
        {
            "type": "compute",
            "name": "dataAssetComputingService",
            "description": "dataAssetComputingService",
            "datatokenAddress": "0x20e91598bb797eEd2C7D4431a274c2997D080f53",
            "providerEndpoint": "http://localhost:8030/",
            "timeout": 3600,
            "privacy": {
                "allowRawAlgorithm": False,
                "allowNetworkAccess": False,
                "publisherTrustedAlgorithms": [],
                "publisherTrustedAlgorithmPublishers": [],
            },
            "files": {
                "files": [
                    {
                        "name": "build_model",
                        "checksum": "efb2c764274b745f5fc37f97c6b0e761",
                        "contentLength": "4535431",
                        "contentType": "text/plain",
                        "encoding": "UTF-8",
                        "compression": "zip",
                    }
                ],
                "encryptedFiles": "encryptedFiles",
            },
        }
    ],
}
