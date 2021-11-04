#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
json_dict = {
    "@context": ["https://w3id.org/did/v1"],
    "id": "did:op:0c184915b07b44c888d468be85a9b28253e80070e5294b1aaed81c2f0264e430",
    "created": "2000-10-31T01:30:00.000-05:00",
    "updated": "2000-10-31T01:30:00.000-05:00",
    "version": "v4.0.0",
    "chainId": 1337,
    "metadata": {
        "name": "Ocean protocol white paper",
        "type": "dataset",
        "description": "Ocean protocol white paper -- description",
        "author": "Ocean Protocol Foundation Ltd.",
        "license": "CC-BY",
        "contentLanguage": "en-US",
        "tags": ["white-papers"],
        "additionalInformation": {"test-key": "test-value"},
        "links": [
            "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-daily/",
            "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/"
            "http://data.ceda.ac.uk/badc/ukcp09/",
        ],
    },
    "services": [
        {
            "type": "access",
            "datatokenAddress": "0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687",
            "name": "Download service",
            "description": "Download service",
            "providerEndpoint": "http://localhost:8030/",
            "timeout": 0,
            "files": {
                "files": [
                    {
                        "checksum": "efb2c764274b745f5fc37f97c6b0e761",
                        "contentType": "text/csv",
                        "checksumType": "MD5",
                        "contentLength": "4535431",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
                    },
                    {
                        "checksum": "efb2c764274b745f5fc37f97c6b0e761",
                        "contentType": "text/csv",
                        "contentLength": "4535431",
                        "resourceId": "access-log2018-02-13-15-17-29-18386C502CAEA932",
                    },
                    {"contentType": "text/csv"},
                ],
                "encryptedFiles": "encryptedFiles",
            },
        }
    ],
}
