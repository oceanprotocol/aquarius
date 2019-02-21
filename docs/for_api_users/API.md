## API

### DDO

- **GET /api/v1/aquarius/assets**  
  _Get all assets ids._
- **GET /api/v1/aquarius/assets/ddo**  
  _Get ddo of all assets_
- **POST /api/v1/aquarius/assets/ddo**  
  _Resgister ddo of a new asset.
    You have to pass a json with the same structure as the following. 
    The fields **@context, id, publicKey, authentication** and **services** are required._
    ```json
    {
      "@context": "https://w3id.org/future-method/v1",
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
      }],
      "authentication": [
      {
        "type": "RsaSignatureAuthentication2018",
        "publicKey": "did:op:123456789abcdefghi#keys-1"
      }, {
        "type": "ieee2410Authentication2018",
        "publicKey": "did:op:123456789abcdefghi#keys-2"
      }], 
      "service": [
      {
        "type": "Consume",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/consume?pubKey=${pubKey}&serviceId={serviceId}&url={url}"
      }, {
        "type": "Compute",
        "serviceEndpoint": "http://mybrizo.org/api/v1/brizo/services/compute?pubKey=${pubKey}&serviceId={serviceId}&algo={algo}&container={container}"
      }, {
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
          "additionalInformation" : {
            "updateFrecuency": "yearly",
            "structuredMarkup" : [
              { "uri" : "http://skos.um.es/unescothes/C01194/jsonld", "mediaType" : "application/ld+json"},
              { "uri" : "http://skos.um.es/unescothes/C01194/turtle", "mediaType" : "text/turtle"}]
          }
        }
      }]
    }
    ```
- **GET /api/v1/aquarius/assets/ddo/query**  
  _Get a list of ddos that match with a text query.
   The request is waiting for the next arguments:_
   - text(required): word that you are searching in the documents
   - sort: a dictionary with the field that you want to order. 1 is ascendant order and -1 descendant. Ex. {"field1":1}
   - offset: Number of objects shows in each page.
   - page: Page to show.
- **POST /api/v1/aquarius/assets/ddo/query**  
  _Get a list of ddos that match with the query executed.
    The request is waiting for the next data json:_
    ```json
    {
      "query": {"name_of_query":["parameters"]},
      "sort": {"field":1},
      "offset": 100,
      "page": 0
    } 
    ```
    Currently we are supporting the following queries:
    - price
        
        Could receive one or two parameters. If you only pass one assumes that your query is going to start from 0 to your value.
            
        Next query:
        `query:{"price":[0,10]}`
        
        It is transformed to:
        `{"service.metadata.base.price":{"$gt": 0, "$lt": 10}}`
        
    - license
        
        It is going to retrieve all the documents with license that you are passing in the parameters, 
        if you do not pass any value retrieve all.
            
        `{"license":["Public domain", "CC-YB"]}`
        
    - type
        
        It is going to check that the following service types are included in the ddo.
        
        `{"type":["Access", "Metadata"]}`
    
    - sample
    
        Check that the metadata include a sample that contains a link of type sample. Do not take parameters.
        
        `{"sample":[]}`
        
    - categories
    
        Retrieve all the values that contain one of the specifies categories.
        
        `{"categories":["weather", "meteorology"]}`
        
    - created
    
        Retrieve all the values that has been created after a specified date. 
        The parameters available are 'today', 'lastWeek', 'lastMonth', 'lastYear'. If you pass more than one take the bigger interval.
        If you do not pass any parameter retrieve everything.
        
        `{"created":["today"]}`
        
    - updatedFrequency
    
        Retrieve all the values that contain one of the specifies updated frecuencies.
        
        `{"updatedFrequency":["monthly"]}`
        
    - text 
    
        Retrieve all the values that match with the text sent.

        `{"text":["weather"]}`
    
- **PUT /api/v1/aquarius/assets/ddo/{id}**  
  _Update ddo of an existing asset. You should pass a json similiar to the post with your update._
- **DELETE /api/v1/aquarius/assets/ddo/{id}**  
  _Retire ddo of an existing asset. You should pass de id of the asset in the request._
- **GET /api/v1/aquarius/assets/ddo/{id}**  
  _Retrieve ddo of a particular asset. You should pass de id of the asset in the request._


### Metadata
- **GET /api/v1/aquarius/assets/metadata/{id}**  
  _Get metadata of a particular asset. You should pass de id of the asset in the request._
