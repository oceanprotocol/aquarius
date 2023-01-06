# Aquarius REST API

## Assets

### **Get** `/api/aquarius/assets/ddo/<did>`

- Description

    Get DDO of a particular asset.

- Parameters

    | name | description      | type   | in   | required |
    |------|------------------|--------|------|----------|
    | `did`| DID of the asset | string | path | true     |

- Example

    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/ddo/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
    ```

- Responses
    - 200
        - content-type: json
        - description: On successful operation returns DDO information.

    - 404
        - content-type: json
        - description: This asset DID is not in ES.
        - response body:
            ```JSON
            {
                "error": "Asset DID <did> not found in Elasticsearch."
            }
            ```

### **GET** `/api/aquarius/assets/metadata/<did>`

- Description

    Get metadata of a particular asset.

- Parameters

    | name | description      | type   | in   | required |
    |------|------------------|--------|------|----------|
    | `did`| DID of the asset | string | path | true     |

- Example

    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/metadata/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
    ```
- Responses
    - 200
        - content-type: json
        - description: successful operation.

    - 404
        - content-type: json
        - description: This asset DID is not in ES.
        - response body:
            ```JSON
            {
                "error": "Error encountered while retrieving metadata: NotFoundError(404, '{\"_index\":\"aquarius\",\"_type\":\"_doc\",\"_id\":\"<did>\",\"found\":false}')."
            }
            ```

### **POST** `/api/aquarius/assets/names`

- Description

    Get names of assets as specified in the payload.

- Parameters

    | name    | description        | type | in   | required |
    |---------|--------------------|------|------|----------|
    | `didList` | list of asset DIDs | list | body | true     |

- Example

    ```bash
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/names' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "didList" : ["did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479"]
    }'
    ```
- Responses
    - 200
        - content-type: json
        - description: successful operation.
        - response body:
            ```JSON
            {"did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479": "Ocean Protocol Technical Whitepaper"}
            ```
    - 400
        - content-type: json
        - description: This asset DID is not in ES.
        - response body:
            ```JSON
            {
            "error": "The requested didList can not be empty."
            }
            ```

### **POST** `/api/aquarius/assets/query`

- Description

    Run a native ES query. Body must be a valid json object.

- Example

    ```bash
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query' \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "query": {
            "match_all": {}
        }
    }'
    ```

- Responses
    - 200
        - content-type: json
    - 500
        - description: elasticsearch exception

### **POST** `/api/aquarius/assets/ddo/validate`

- Description

    Validate DDO content. Cosumes `application/octet-stream`

- Example

    ```bash
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/ddo/validate' \
    --header 'Content-Type: application/json' \
    --data-raw '<json_body>'
    ```
- Valid body

    ```JSON
        {
            "@context": ["https://w3id.org/did/v1"],
            "id": "did:op:56c3d0ac76c02cc5cec98993be2b23c8a681800c08f2ff77d40c895907517280",
            "version": "4.3.0",
            "chainId": 1337,
            "nftAddress": "0xabc",
            "metadata": {
                "created": "2000-10-31T01:30:00.000-05:00Z",
                "updated": "2000-10-31T01:30:00.000-05:00",
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
                    "http://data.ceda.ac.uk/badc/ukcp09/data/gridded-land-obs/gridded-land-obs-averages-25km/",
                    "http://data.ceda.ac.uk/badc/ukcp09/"
                ]
            },
            "services": [
                {
                    "id": "test",
                    "type": "access",
                    "datatokenAddress": "0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687",
                    "name": "Download service",
                    "description": "Download service",
                    "serviceEndpoint": "http://172.15.0.4:8030/",
                    "timeout": 0,
                    "files": "encryptedFiles"
                }
            ]
        }
    ```

- Responses:
    - 200

        - description: successfully request.

    - 400

        - description: Invalid DDO format

    - 500

        - description: Error


### **POST** `/api/aquarius/assets/triggerCaching`

- Description

    Manually triggers DDO caching based on a transactionId containing either MetadataCreated or MetadataUpdated event(s).

- Parameters

    | name           | description                         | type   | in   | required |
    |----------------|-------------------------------------|--------|------|----------|
    | `transactionId`| transaction ID                      | string | path | true     |
    | `logIndex`     | custom log index for the transaction| int    | path | false    |
    | `chainId`      | chain id                            | int    | path | true     |

- Example

    ```bash
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/triggerCaching' \
    --header 'Content-Type: application/json' \
    --data-raw '<json_body>'
    ```
- Valid body

    ```JSON
        {
            "transactionId": "0x945596edf2a26d127514a78ed94fea86b199e68e9bed8b6f6d6c8bb24e451f27",
            "logIndex": 0,
            "chain_id": 1
        }
    ```

- Responses:
    - 200

        - description: triggering successful, updated asset returned

    - 400

        - description: request issues: either log index not found, or neither of MetadataCreated, MetadataUpdated found in tx log

    - 500

        - description: Error


## Chains

### **GET** `/api/aquarius/chains/list`

- Description

    Get chains list

- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/chains/list'
    ```

- Response
    - 200

        - Description: Successful request
        - Body
            ```JSON
            {   "246": true, "3": true, "137": true,
                "2021000": true, "4": true, "1": true,
                "56": true, "80001": true, "1287": true
            }
            ```

### **GET** `/api/aquarius/chains/status/{chain_id}`

- Description

    Get index status for a specific chain_id

- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/chains/status/137'
    ```

- Response
    - 200

        - Description: Successful request
        - Body
            ```JSON
            {"last_block": 25198729,
            "version": "4.4.1"}
            ```

## State

### **GET** `/api/aquarius/state/retryQueue`

- Description

    Returns all queue retry logs

- Parameters

    | name           | description                          |
    |----------------|--------------------------------------|
    | `did`          | filter for did                       |
    | `chainId`      | chain id                             |
    | `nft`          | nft                                  |
    | `type`         | retry event type (tx, event or block)|


- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/state/retryQueue?chainId=1'
    ```


### **GET** `/api/aquarius/state/ddo`

- Description

    Returns ddo(s) state(s)

- Parameters for filtering:

    | name           | description                          |
    |----------------|--------------------------------------|
    | `did`          | did                                  |
    | `chainId`      | chain id                             |
    | `nft`          | nft                                  |
    | `txId`         | tx id                                |
    


- Examples
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/state/ddo?did=did:op:9c1235050bcd51c8ec9a7058110102c9595136834911c315b4f739bc9a880b8e
    ```

    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/state/ddo?nft=0xC7ED00725AAb7E679fCB46C9620115fE0B6dD94a
    ```

## Others


### **GET** `/`

- Description

    Get version, plugin, and software information.

- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/'
    ```

- Response
    - 200
        - Description: Successful request
        - Body
            ```JSON
            {
                "plugin": "elasticsearch",
                "software": "Aquarius",
                "version": "3.1.2"
            }
            ```

### **GET** `/health`

- Description

    Get health status

- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/health'
    ```

- Response
    - 200
        - Description: Successful request
        - Body
            ```text
            Elasticsearch connected
            ```

### **GET** /spec

- Description

    Get swagger spec

- Example
    ```bash
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/spec'
    ```

- Response
    - 200
        - Description: Successful request

### Postman documentation

Click <a href="https://documenter.getpostman.com/view/2151723/UVkmQc7r" target="_blank">here</a> to explore the documentation and more examples in postman.
