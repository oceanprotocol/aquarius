<!--
Copyright 2021 Ocean Protocol Foundation
SPDX-License-Identifier: Apache-2.0
-->
[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

[![Docker Build Status](https://img.shields.io/docker/build/oceanprotocol/aquarius.svg)](https://hub.docker.com/r/oceanprotocol/aquarius/) [![Travis (.com)](https://img.shields.io/travis/com/oceanprotocol/aquarius.svg)](https://travis-ci.com/oceanprotocol/aquarius)
[![Maintainability](https://api.codeclimate.com/v1/badges/411b97f9749f9dcac801/maintainability)](https://codeclimate.com/github/oceanprotocol/aquarius/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/411b97f9749f9dcac801/test_coverage)](https://codeclimate.com/github/oceanprotocol/aquarius/test_coverage)
[![PyPI](https://img.shields.io/pypi/v/ocean-aquarius.svg)](https://pypi.org/project/ocean-aquarius/)
[![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/aquarius.svg)](https://github.com/oceanprotocol/aquarius/graphs/contributors)

# Aquarius

> Off-chain database cache for metadata that is published on-chain.

Aquarius enables fast query operations on datasets metadata. It consists of:
- a Flask application to support fetching and searching metadata, and
- a blockchain events monitor that picks up new metadata published on-chain, then stores it in the database backend (elasticsearch).

It's part of the [Ocean Protocol](https://oceanprotocol.com) toolset.

## What Aquarius does
* Aquarius runs a Flask RESTful server to support fetching and searching metadata of datasets that are published on-chain
  * The metadata is published on-chain via the Metadata smartcontract:
    * Metadata is first compressed then published on-chain
    * The compressed metadata on-chain is not kept in storage, but rather is captured in an event log named `MetadataCreated`
    * The id (DID) of the dataset asset is the Datatoken address, off-chain the did consist of `did:op:` prepended to the datatoken address
* Aquarius runs an events monitor that watches the:
  * `MetadataCreated` event from the `Metadata` smartcontract
    * Reads the events `data` argument, decompresses the metadata json object
      then runs schema validation before saving it to the database

## Setup
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

# Start a HTTP server inside the events monitor. This is usefull for K8 live probing. You must simply access the root endpoint on port 5001. IE: http://172.0.0.1:5001 which will respond with 200 OK if the events thread is up.  Otherwise, there will be no response
EVENTS_HTTP
  accepted values:
    "1" to enable
```
And these are optional
```bash
# If Aquarius API is available. Default: 1
RUN_AQUARIUS_SERVER
# Use this to decrypt metadata when read from the blockchain event log
EVENTS_ECIES_PRIVATE_KEY
# Aquarius should cache only encrypted ddo. This will make aquarius unable to cache all other datasets on the network !!!!
ONLY_ENCRYPTED_DDO
# Path to the `address.json` file or any json file that has the deployed contracts addresses
ADDRESS_FILE
# Specify the network name to use for reading the contracts addresses from the `ADDRESS_FILE`.
# If not set, the netwrok name is derived from current network id or from the `EVENTS_RPC` value
NETWORK_NAME
# Skip caching metadata of publishers that are not in this list
ALLOWED_PUBLISHERS
# Metadata contract address. Optional. Use it if you want to overwrite values from ocean-contracts
METADATA_CONTRACT_ADDRESS
# The block number of `Metadata` contract deployment
METADATA_CONTRACT_BLOCK
# Enable the use of poa_middleware if the network is a POA network such as Rinkeby
USE_POA_MIDDLEWARE
# if set to 1, read events from the first Metadata and BFactory block number, or a specific block number (used for debugging)
IGNORE_LAST_BLOCK
# When scanning for events, limit the chunk size. Infura accepts 10k blocks, but others will take only 1000 (default value)
BLOCKS_CHUNK_SIZE
# URLs of asset purgatory and account purgatory. If neither exists, the purgatory will not be processed
ASSET_PURGATORY_URL
ACCOUNT_PURGATORY_URL
# Customise purgatory update time (in number of minutes)
PURGATORY_UPDATE_INTERVAL
# The URL of the RBAC Permissions Server. If set, Aquarius will check permissions with RBAC. Leave empty/unset to skip RBAC permission checks.
RBAC_SERVER_URL
# Whether to start clean and reindex events on chain id
EVENTS_CLEAN_START
```
## Running Aquarius for multiple chains
If you want to index multiple chains using a single Aquarius instance, you should do the following:
 * Run one or more pods, with RUN_AQUARIUS_SERVER =1 , RUN_EVENTS_MONITOR = 0 AND EVENTS_ALLOW = 0.  This will only serve API requests
 * For each chain, start a pod with the following envs:
     * Set RUN_EVENTS_MONITOR = 1 and RUN_AQUARIUS_SERVER = 0
     * Set coresponding EVENTS_RPC, NETWORK_NAME, BLOCKS_CHUNK_SIZE, METADATA_CONTRACT_BLOCK, METADATA_CONTRACT_ADDRESS etc


## For Aquarius Operators

If you're developing a marketplace, you'll want to run Aquarius and several other components locally,
and the easiest way to do that is to use Barge. See the instructions
in [the Barge repository](https://github.com/oceanprotocol/barge).

## For Aquarius API Users

[Here](https://docs.oceanprotocol.com/references/aquarius/) is API documentation.

If you have Aquarius running locally, you can find API documentation at
[http://localhost:5000/api/v1/docs](http://localhost:5000/api/v1/docs) or maybe
[http://0.0.0.0:5000/api/v1/docs](http://0.0.0.0:5000/api/v1/docs).

Tip 1: If that doesn't work, then try `https`.

Tip 2: If your browser shows the Swagger header across the top but says "Failed to load spec." then we found that, in Chrome, if we went to `chrome://flags/#allow-insecure-localhost` and toggled it to Enabled, then relaunched Chrome, it worked.

More details about ontology of the metadata are at
[OEP-8](https://github.com/oceanprotocol/OEPs/tree/master/8).

## For Aquarius Developers

### General Ocean Dev Docs

Ocean's Python code style and related "meta" developer docs are at [oceanprotocol/dev-ocean repo](https://github.com/oceanprotocol/dev-ocean).

### Running Locally, for Dev and Test

Run a Barge instance without Aquarius.

```bash
git clone https://github.com/oceanprotocol/barge
cd barge
./start_ocean.sh  --no-aquarius
```

In a new terminal tab, run the elasticsearch database (required for Aquarius). You can also run this in the background, but it helps development to see all output separately.

```bash
export ES_VERSION=6.6.2
export ES_DOWNLOAD_URL=https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}.tar.gz
wget ${ES_DOWNLOAD_URL}
tar -xzf elasticsearch-${ES_VERSION}.tar.gz
./elasticsearch-${ES_VERSION}/bin/elasticsearch
```

In yet another tab, clone this repository:

```bash
git clone git@github.com:oceanprotocol/aquarius.git
cd aquarius/
```

Install Aquarius's OS-level requirements:

```bash
sudo apt update
sudo apt install python3-dev
```

It is recommended that you create and activate a virtual environment in order to install the dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

At this point, with the Elasticsearch database already running, now you can start the Aquarius server:

```bash
pip install wheel
pip install -r requirements.txt
export FLASK_APP=aquarius/run.py
export AQUARIUS_CONFIG_FILE=config.ini
flask run
```

That will use HTTP (i.e. not SSL/TLS).

If you are a contributor, make sure you install the pre-commit hooks using the command `pre-commit install`. This will make sure your imports are sorted and your code is properly formatted before committing.

The proper way to run the Flask application is using an application server such as Gunicorn. This allow you to run using SSL/TLS.
You can generate some certificates for testing by doing:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

and when it asks for the Common Name (CN), answer `localhost`

Then edit the config file `config.ini` so that:

```yaml
aquarius.url = http://localhost:5000
```

Then execute this command:

```bash
gunicorn --certfile cert.pem --keyfile key.pem -b 0.0.0.0:5000 -w 1 aquarius.run:app
```

### Configuration

You can pass the configuration using the AQUARIUS_CONFIG_FILE environment variable (recommended) or locating your configuration in config.ini file.

In the configuration there are now two sections:

- oceandb: Contains different values to connect with elasticsearch. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- resources: In this section we are showing the url in which the aquarius is going to be deployed.

```yaml
[resources]
aquarius.url = http://localhost:5000
```

### Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

If you want to run a test individually, without using tox, run `pytest test_file_path.py::test_specific_test`.
In this case, if some environment variables are not set, pytest will default to those defined in `pytest.ini` (defined in the project root directory). These variables are the same as the ones tox.ini defines.

### New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

## License

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
