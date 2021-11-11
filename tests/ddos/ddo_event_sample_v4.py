#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
ddo_event_sample_v4 = {
    "@context": ["https://w3id.org/did/v1"],
    "id": "did:op:ffa5037987b74fbab600d7515605146bb7babcb929c94c60ba93ac5ceda56775",
    "created": "2000-10-31T01:30:00.000-05:00",
    "updated": "2000-10-31T01:30:00.000-05:00",
    "version": "4.0.0",
    "chainId": 1337,
    "metadata": {
        "type": "dataset",
        "name": "Event DDO sample",
        "description": "Event DDO sample",
        "author": "Met Office",
        "license": "CC-BY",
        "contentLanguage": "en-US",
        "tags": ["samples"],
    },
    "services": [
        {
            "type": "access",
            "datatokenAddress": "0x20e91598bb797eEd2C7D4431a274c2997D080f53",
            "name": "dataAssetAccess",
            "description": "dataAssetAccess",
            "providerEndpoint": "http://localhost:8030/",
            "timeout": 0,
        },
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
        },
    ],
}
