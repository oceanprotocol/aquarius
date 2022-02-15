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
    curl --location --request GET 'https://aquarius.oceanprotocol.com/api/v1/aquarius/assets/ddo/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
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
    curl --location --request GET 'https://aquarius.oceanprotocol.com/api/v1/aquarius/assets/metadata/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
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
    curl --location --request POST 'https://aquarius.oceanprotocol.com/api/v1/aquarius/assets/names' \
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

### POST `/api/aquarius/assets/query`

### POST `/api/aquarius/assets/ddo/validate`

## Chains

### **GET** `/api/aquarius/chains/list`

### **GET** `/api/aquarius/chains/status/{chain_id}`


## Others

/health
