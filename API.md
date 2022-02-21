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
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/assets/ddo/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
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
    curl --location --request GET 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/assets/metadata/did:op:CbD7aeecB5DFbABaB9126B5Cf1262dCFBA178479'
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
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/assets/names' \
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
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/assets/query' \
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
    curl --location --request POST 'https://v4.aquarius.oceanprotocol.com/api/aquarius/assets/query/api/v1/aquarius/assets/ddo/validate' \
    --header 'Content-Type: application/json' \
    --data-raw '<json_body>'
    ```

    <details>
        <summary><b><u>Valid json_body</u></b></summary>

        
        {
        "main": {

            "name": "10 Monkey Species Small",
            "dateCreated": 
            "2012-02-01T10:55:11Z",
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
            "type": "dataset"
        },
        "additionalInformation": {
            "description": "EXAMPLE ONLY ",
            "categories": ["image"],
            "tags": ["image data", "classification", "animals"],
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
        
    </details>

- Responses:
    - 200

        - description: successfully request.
    
    - 400

        - description: Invalid DDO format
    
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
            {"last_block": 25198729}
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
           