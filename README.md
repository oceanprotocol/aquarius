<!--
Copyright 2023 Ocean Protocol Foundation
SPDX-License-Identifier: Apache-2.0
-->
[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

[![Aquarius tests](https://github.com/oceanprotocol/aquarius/actions/workflows/pytest.yml/badge.svg)](https://github.com/oceanprotocol/aquarius/actions/workflows/pytest.yml)
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
   * [Running Aquarius locally](#running-aquarius-locally)
   * [Development](#development)
* [License](#license)

# What is Aquarius?

Aquarius is an off-chain, multi-chain cache for metadata that is published on chain, connected to an Elasticsearch database. Aquarius continually monitors the chains for MetadataCreated and MetadataUpdated events, processes these events and adds them to the database. The Aquarius API offers a convenient way to access the medatata without scanning the chain yourself.

Aquarius is part of the [Ocean Protocol](https://oceanprotocol.com) toolset. 🌊

## How is metadata treated?

The metadata is published on-chain as such:

* Metadata is first (optionally) compressed (using lzma) and (strongly recommended) encrypted, then published on-chain
* The metadata on-chain is not kept in storage, but rather is captured in an event log named `MetadataCreated`
* Aquarius defers to the Provider for encryption and decryption. Aquarius and Provider support utf-8 encoded strings. You can look into the encrypt/decrypt flows if you want to learn more, but you will generally not need to go in-depth just to use Aquarius.

For more details on working with OCEAN DIDs check out the [DID concept documentation](https://docs.oceanprotocol.com/core-concepts/did-ddo/).
The [DDO Metadata documentation](https://docs.oceanprotocol.com/core-concepts/did-ddo#metadata) goes into more depth regarding metadata structure.

## Components and architecture

Aquarius is a simple, lightweight scanner and API. It is built using Python, using the Flask framework.

### The Aquarius API

Aquarius provides REST api to fetch the data from off-chain datastore.
Please refer to [API.md](API.md) file for details on the API itself.

### The EventsMonitor

The events monitor runs continuously to retrieve and index the chain Metadata. It saves the results into an Elasticseach database. The monitor reads the events `data` argument, decompresses the metadata json object, then runs schema validation before saving it to the database. The monitor is highly customisable, and it consists of the following components:

- an ElasticsearchInstance, configured through env variables
- an associated MetadataContract, configured through the `METADATA_CONTRACT_ADDRESS` env variable
- a Decryptor class that handles decompression and decryption on the chain data, through communication with Provider
- a set of `ALLOWED_PUBLISHERS`, if such a restriction exists. You can set a limited number of allowed publisher addresses using this env variable.
- a Purgatory, based on the `ASSET_PURGATORY_URL` and `ACCOUNT_PURGATORY_URL` env variables. These mark some assets as being in purgatory (`"isInPurgatory": True`), enabling restrictions for some assets or accounts.
- a VeAllocate, based on the `VEALLOCATE_URL` and `VEALLOCATE_UPDATE_INTERVAL` env variables. This updates the veAllocation for datasets.
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

# Identify instance of Aquarius to Provider, when decrypting assets. Provider may allow or deny decryption based on this address.
PRIVATE_KEY

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

# if set to 1, read events from the first Metadata and BFactory block number, or a specific block number (used for debugging)
IGNORE_LAST_BLOCK

# When scanning for events, limit the chunk size. Infura accepts 10k blocks, but others will take only 1000 (default value)
BLOCKS_CHUNK_SIZE

# URLs of asset purgatory and account purgatory. If neither exists, the purgatory will not be processed. The list should be formatted as a list of dictionaries containing the address and reason. See https://github.com/oceanprotocol/list-purgatory/blob/main/list-accounts.json for an example
# IMPORTANT.  If you are running multiple aquarius event monitors (for multiple chains), make sure that only one event-monitor will handle purgatory
ASSET_PURGATORY_URL
ACCOUNT_PURGATORY_URL

# Customise purgatory update (refresh) time (in number of minutes)
PURGATORY_UPDATE_INTERVAL

# URL for getting the veAllocation list. If not exists, the veAllocate will not be processed. Possible values are: https://df-sql.oceandao.org/nftinfo for mainnet and https://test-df-sql.oceandao.org/nftinfo for goerli, because veOCEAN is deployed only on this networks. All other networks SHOULD NOT HAVE this defined.  The list should be formatted as a list of dictionaries containing chainID,nft_addr and ve_allocated
VEALLOCATE_URL

# Customise veAllocate update (refresh) time (in number of minutes)
VEALLOCATE_UPDATE_INTERVAL

# The URL of the RBAC Permissions Server. If set, Aquarius will check permissions with RBAC. Leave empty/unset to skip RBAC permission checks.
RBAC_SERVER_URL

# Whether to start clean and reindex events on chain id
EVENTS_CLEAN_START

# Subgraph URLs in the form of a json-dumped string mapping chain_ids to subgraph urls.
SUBGRAPH_URLS

# Process a queue with failed assets, e.g. retry where temporary network flukes or similar conditions caused a failure
PROCESS_RETRY_QUEUE

# For how long to retry such an event, before giving up. Defaults to 2 weeks
PROCESS_RETRY_MAX_HOLD

# Customize sleep time for events monitor between checking for new events. Defaults to 30 seconds
EVENTS_MONITOR_SLEEP_TIME
# Customize sleep time for events monitor between queue processing. Defaults to 60 seconds
EVENTS_PROCESS_QUEUE_SLEEP_TIME
# Customize sleep time for events monitor between updating ve_allocate. Defaults to 300 seconds
EVENTS_VE_ALLOCATE_SLEEP_TIME
# Customize sleep time for events monitor between checking for nft transfers. Defaults to 300 seconds
EVENTS_NFT_TRANSFER_SLEEP_TIME
# Customize sleep time for events monitor between checking for purgatory lists. Defaults to 300 seconds
EVENTS_PURGATORY_SLEEP_TIME
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

[Here](https://docs.oceanprotocol.com/api-references/aquarius-rest-api) is API documentation. You can find more details about the ontology of the metadata in the [Ocean documentation](https://docs.oceanprotocol.com/core-concepts/did-ddo#metadata).

If you have Aquarius running locally, you can find a Swagger API documentation at [http://localhost:5000/api/docs](http://localhost:5000/api/docs) or maybe [http://0.0.0.0:5000/api/docs](http://0.0.0.0:5000/api/docs).

- Tip 1: If that doesn't work, then try `https`.
- Tip 2: If your browser shows the Swagger header across the top but says "Failed to load spec." then we found that, in Chrome, if we went to `chrome://flags/#allow-insecure-localhost` and toggled it to Enabled, then relaunched Chrome, it worked.

## Running Aquarius locally

For testing purposes, running Aquarius from [barge](https://github.com/oceanprotocol/barge/) should suffice, but if you want to run your own version of Aquarius (with any configurations or alterations), you can do that by following the instructions in [the developers documentation](developers.md).

## Development

If you want to improve or customise Aquarius, you're our favourite kind of person! Go to [the developers flow](developers.md) to learn more about how you can contribute.

# License

Copyright 2022 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
