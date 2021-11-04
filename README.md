<!--
Copyright 2021 Ocean Protocol Foundation
SPDX-License-Identifier: Apache-2.0
-->
[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

[![Aquarius tests](https://github.com/oceanprotocol/aquarius/actions/workflows/tox.yml/badge.svg)](https://github.com/oceanprotocol/aquarius/actions/workflows/tox.yml)
[![black](https://github.com/oceanprotocol/aquarius/actions/workflows/black.yml/badge.svg)](https://github.com/oceanprotocol/aquarius/actions/workflows/black.yml)
[![Docker Build Status](https://img.shields.io/docker/cloud/build/oceanprotocol/aquarius.svg)](https://hub.docker.com/r/oceanprotocol/aquarius/)
[![Maintainability](https://api.codeclimate.com/v1/badges/411b97f9749f9dcac801/maintainability)](https://codeclimate.com/github/oceanprotocol/aquarius/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/411b97f9749f9dcac801/test_coverage)](https://codeclimate.com/github/oceanprotocol/aquarius/test_coverage)
[![PyPI](https://img.shields.io/pypi/v/ocean-aquarius.svg)](https://pypi.org/project/ocean-aquarius/)
[![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/aquarius.svg)](https://github.com/oceanprotocol/aquarius/graphs/contributors)

# Aquarius

* [What is Aquarius?](#what-is-aquarius)
   * [How is metadata treated?](#how-is-metadata-treated)
   * [Components and architecture](#components-and-architecture)
      * [The Aquarius API](#the-aquarius-api)
      * [The EventsMonitor](#the-eventsmonitor)
* [Aquarius Setup](#aquarius-setup)
   * [Running Aquarius for multiple chains](#running-aquarius-for-multiple-chains)
* [Using Aquarius](#using-aquarius)
   * [Quickstart](#quickstart)
   * [Learn about Aquarius API](#learn-about-aquarius-api)
   * [Development](#development)
* [License](#license)

# What is Aquarius?

Aquarius is an off-chain, multi-chain cache for metadata that is published on chain, connected to an Elasticsearch database. Aquarius continually monitors the chains for MetadataCreated and MetadataUpdated events, processes these events and adds them to the database. The Aquarius API offers a convenient way to access the medatata without scanning the chain yourself.

Aquarius is part of the [Ocean Protocol](https://oceanprotocol.com) toolset. 🌊

## How is metadata treated?

The metadata is published on-chain via the Metadata smartcontract:

* Metadata is first compressed (using lzma), then published on-chain
* The compressed metadata on-chain is not kept in storage, but rather is captured in an event log named `MetadataCreated`
* The id (DID) of the dataset asset is the Datatoken address, off-chain the did consist of `did:op:` prepended to the datatoken address

For more details on working with OCEAN DIDs check out the [DID concept documentation](https://docs.oceanprotocol.com/concepts/did-ddo/).
The [DDO Metadata documentation](https://docs.oceanprotocol.com/concepts/ddo-metadata/) goes into more depth regarding metadata structure.

## Components and architecture

Aquarius is a simple, lightweight scanner and API. It is built using Python, using the Flask framework.

### The Aquarius API

- `GET api/v1/aquarius/assets/ddo/<did>`: retrieve asset contents for the given DID
- `GET api/v1/aquarius/assets/metadata/<did>`: retrieve metadata associated to the given DID
- `POST api/v1/aquarius/assets/names/`: takes in a list of DIDs of the format `["did:op:123455644356", "did:op:533443322223344"]` and returns a dictionary of correspondence between the given DIDs and the asset name
- `POST api/v1/aquarius/assets/query`: takes in a native Elasticsearch query, passes it over to Elasticsearch and returns the unformatted results, as given by the Elasticsearch instance. Please note that Elasticsearch imposes a limitation of 10K results. If you get a Transport Error indicating such a problem, try to refine your search.
- `POST api/v1/aquarius/assets/ddo/validate-remote`: accepts a DDO sample and validates them in the local remote format, respectively. Please use this endpoint to validate your OCEAN DDOs.
- `POST api/v1/aquarius/assets/ddo/encrypt` and `POST api/v1/aquarius/assets/ddo/encryptashex`: encrypts the asset using the `EVENTS_ECIES_PRIVATE_KEY` env var. Unencrypted assets can be read by any Aquarius instance, but if you are running a private Aquarius, this makes your assets private.
- `GET api/v1/aquarius/chains/list`: lists all chains indexed by the Aquarius version
- `GET api/v1/aquarius/chains/status/<chain_id>`: shows the status of the chain corresponding to the given `chain_id`

### The EventsMonitor

The events monitor runs continuously to retrieve and index the chain Metadata. It saves the results into an Elasticseach database. The monitor reads the events `data` argument, decompresses the metadata json object, then runs schema validation before saving it to the database. The monitor is highly customisable, and it consists of the following components:

- an ElasticsearchInstance, configured through the config.ini or env variables
- an associated MetadataContract, configured through the config.ini or the `METADATA_CONTRACT_ADDRESS` env variable
- a Decryptor configured based on the `ECIES_EVENTS_PRIVATE_KEY`, if one exists. The Decryptor handles decompression and decryption on the chain data.
- a set of `ALLOWED_PUBLISHERS`, if such a restriction exists. You can set a limited number of allowed publisher addresses using this env variable.
- a Purgatory, based on the `ASSET_PURGATORY_URL` and `ACCOUNT_PURGATORY_URL` env variables. These mark some assets as being in purgatory (`"isInPurgatory": True`), enabling restrictions for some assets or accounts.
- start blocks, if such defined using `BFACTORY_BLOCK` and `METADATA_CONTRACT_BLOCK`. These start blocks are coroborated with the last stored blocks per Elasticsearch, to avoid indexing multiple times

The EventsMonitor processes block chunks as defined using `BLOCKS_CHUNK_SIZE`. For each block, it retrieves all `MetadataCreated` and `MetadataUpdated` events, and these events are processed inside the `MetadataCreatedProcessor` and `MetadataUpdatedProcessor` classes. These processors run the following flow:

- optionally check permissions with the `RBAC_SERVER_URL` and `ALLOWED_PUBLISHERS`
- decompresses and optionally decrypts the asset metadata
- checks whether the asset needs to be sent to purgatory
- creates the JSON record and saves it in Elasticsearch
- if a `MetadataUpdated` event is detected on an asset that does not exist in Elasticsearch already, then it is treated as a `MetadataCreated` event.

# Aquarius Setup
The following environment variables are required for running Aquarius:

```
# URL of ethereum network.
# Recommendation: when connecting to an official network, create an Infura project id and set this
# to use the Infura url including the project id
EVENTS_RPC
  examples:
  "http://172.15.0.3:8545", "wss://rinkeby.infura.io/ws/v3/INFURA_ID"

# Use this to run the EventsMonitor in a thread from the main Flask app
EVENTS_ALLOW
  accepted values:
    "0" to disable
    "1" to enable

# Run the EventsMonitor in a separate process, overrides `EVENTS_ALLOW`.
# This is only used when running in `docker` container
RUN_EVENTS_MONITOR
  accepted values:
    "0" to disable
    "1" to enable

# Start a HTTP server inside the events monitor. This is useful for K8 live probing. You must simply access the root endpoint on port 5001. IE: http://172.0.0.1:5001 which will respond with 200 OK if the events thread is up.  Otherwise, there will be no response
EVENTS_HTTP
  accepted values:
    "1" to enable
```
And these are optional
```bash
# Enables the Aquarius API. Default: 1, disable if you only want to use the events monitor, without exposing an API.
RUN_AQUARIUS_SERVER

# Enable encryption and decryption of the metadata, when read from the blockchain event log
EVENTS_ECIES_PRIVATE_KEY

# When set to 1, Aquarius only caches encrypted (private) ddos. This will prevent Aquarius from caching all other datasets on the network
ONLY_ENCRYPTED_DDO

# Path to the `address.json` file or any json file that has the deployed contracts addresses
ADDRESS_FILE

# Specify the network name to use for reading the contracts addresses from the `ADDRESS_FILE`.
# If not set, the network name is derived from current network id or from the `EVENTS_RPC` value, by splitting out the wss://, http:// or https:// part and the suffixes
NETWORK_NAME

# Restrict metadata caching to publishers in this list. It is a list of publisher addresses.
ALLOWED_PUBLISHERS

# Metadata contract address. Use it if you want to overwrite values from ocean-contracts
METADATA_CONTRACT_ADDRESS

# The block number of `Metadata` contract deployment
METADATA_CONTRACT_BLOCK

# Enable the use of poa_middleware if the network is a POA network such as Rinkeby. (no need to set for rinkeby specifically, since that is already treated in the code, but any other POA network should have this flag setup)
USE_POA_MIDDLEWARE

# if set to 1, read events from the first Metadata and BFactory block number, or a specific block number (used for debugging)
IGNORE_LAST_BLOCK

# When scanning for events, limit the chunk size. Infura accepts 10k blocks, but others will take only 1000 (default value)
BLOCKS_CHUNK_SIZE

# URLs of asset purgatory and account purgatory. If neither exists, the purgatory will not be processed. The list should be formatted as a list of dictionaries containing the address and reason. See https://github.com/oceanprotocol/list-purgatory/blob/main/list-accounts.json for an example
ASSET_PURGATORY_URL
ACCOUNT_PURGATORY_URL

# Customise purgatory update (refresh) time (in number of minutes)
PURGATORY_UPDATE_INTERVAL

# The URL of the RBAC Permissions Server. If set, Aquarius will check permissions with RBAC. Leave empty/unset to skip RBAC permission checks.
RBAC_SERVER_URL

# Whether to start clean and reindex events on chain id
EVENTS_CLEAN_START
```
## Running Aquarius for multiple chains

If you want to index multiple chains using a single Aquarius instance, that is possible. The OCEAN version of Aquarius uses this exact flow. To enable multi-chain indexing, these are the necessary steps:
 * Run one or more pods, with `RUN_AQUARIUS_SERVER=1` , `RUN_EVENTS_MONITOR=0` and `EVENTS_ALLOW=0`.  This basically enables only the API part of Aquarius.
 * For each chain, start a pod with the following env variables:
     * Set `RUN_EVENTS_MONITOR=1` and `RUN_AQUARIUS_SERVER=0` (run only the EventsMonitor part of Aquarius)
     * Set coresponding `EVENTS_RPC`, `NETWORK_NAME`, `BLOCKS_CHUNK_SIZE`, `METADATA_CONTRACT_BLOCK`, `METADATA_CONTRACT_ADDRESS` etc.

A list of deployment values and schematics [can be found here](https://github.com/oceanprotocol/aquarius/tree/main/deployment)

Voilà! You are now running a multi-chain Aquarius.

# Using Aquarius

## Quickstart

If you're developing a marketplace, you'll want to run Aquarius and several other components locally. The easiest way to do that is to use Barge. See the instructions in [the Barge repository](https://github.com/oceanprotocol/barge).

## Learn about Aquarius API

[Here](https://docs.oceanprotocol.com/references/aquarius/) is API documentation. You can find more details about the ontology of the metadata in the [Ocean documentation](https://docs.oceanprotocol.com/concepts/ddo-metadata/).

If you have Aquarius running locally, you can find a Swagger API documentation at [http://localhost:5000/api/v1/docs](http://localhost:5000/api/v1/docs) or maybe [http://0.0.0.0:5000/api/v1/docs](http://0.0.0.0:5000/api/v1/docs).

- Tip 1: If that doesn't work, then try `https`.
- Tip 2: If your browser shows the Swagger header across the top but says "Failed to load spec." then we found that, in Chrome, if we went to `chrome://flags/#allow-insecure-localhost` and toggled it to Enabled, then relaunched Chrome, it worked.

## Development

If you want to improve or customise Aquarius, you're our favourite kind of person! Go to [the developers flow](developers.md) to learn more about how you can contribute.

# License

Copyright 2021 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
