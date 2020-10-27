[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Aquarius

> 🐋 Aquarius provides an off-chain database cache for metadata that is published on-chain. 
This enables faster query operations on datasets metadata. 
The latest version of Aquarius consist of a Flask application to support fetching and 
searching metadata and a blockchain events monitor that picks up new metadata published 
on-chain and stores it in the database backend (elasticsearch).

> It's part of the [Ocean Protocol](https://oceanprotocol.com) software stack.

[![Docker Build Status](https://img.shields.io/docker/build/oceanprotocol/aquarius.svg)](https://hub.docker.com/r/oceanprotocol/aquarius/) [![Travis (.com)](https://img.shields.io/travis/com/oceanprotocol/aquarius.svg)](https://travis-ci.com/oceanprotocol/aquarius) [![Codacy coverage](https://img.shields.io/codacy/coverage/10c8fddd5e8547c29de4906410a16ae7.svg)](https://app.codacy.com/project/ocean-protocol/aquarius/dashboard) [![PyPI](https://img.shields.io/pypi/v/ocean-aquarius.svg)](https://pypi.org/project/ocean-aquarius/) [![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/aquarius.svg)](https://github.com/oceanprotocol/aquarius/graphs/contributors)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/aquarius/issues). 🦑🐲**

---

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
  * `LOG_JOIN`, `LOG_EXIT` and `LOG_SWAP` events from the `BPool` smartcontracts
    * Any of these events is an indication that liquidity and price have changed
    * The watcher reads the liquidity of each token in the pool and updates the 
    corresponding metadata in the cache. This information is added to the metadata 
    to allow sorting and searching by price and/or liquidity volume 
 
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
``` 
And these are optional
```bash
# Use this to decrypt metadata when read from the blockchain event log
EVENTS_ECIES_PRIVATE_KEY
# Path to abi files of the ocean contracts
ARTIFACTS_PATH
# Path to the `address.json` file or any json file that has the deployed contracts addresses 
ADDRESS_FILE
# Specify the network name to use for reading the contracts addresses from the `ADDRESS_FILE`.
# If not set, the netwrok name is derived from current network id or from the `EVENTS_RPC` value
NETWORK_NAME
# Skip caching metadata of publishers that are not in this list 
ALLOWED_PUBLISHERS
# The blockNumber of `BFactory` deployment
BFACTORY_BLOCK
# The blockNumber of `Metadata` contract deployment
METADATA_CONTRACT_BLOCK


``` 

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

### Running as a Docker container

First, clone this repository:

```bash
git clone git@github.com:oceanprotocol/aquarius.git
cd aquarius/
```

Then build the Docker image

```bash
docker build -t "myaqua" .
```

Run Docker image

```bash
docker run myaqua
```

To test with other ocean components in `barge` set the `AQUARIUS_VERSION` environment variable to `myaqua`
Then

```bash
./start_ocean.sh
```

The setup for `Aquarius` and Alastic search in `barge` is in `compose-files/aquarius_elasticsearch.yml`

### Running Locally, for Dev and Test

First, clone this repository:

```bash
git clone git@github.com:oceanprotocol/aquarius.git
cd aquarius/
```

Then run elasticsearch database that is a requirement for Aquarius.

```bash
export ES_VERSION=6.6.2 
export ES_DOWNLOAD_URL=https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}.tar.gz
wget ${ES_DOWNLOAD_URL}
tar -xzf elasticsearch-${ES_VERSION}.tar.gz
./elasticsearch-${ES_VERSION}/bin/elasticsearch &
```

Then install Aquarius's OS-level requirements:

```bash
sudo apt update
sudo apt install python3-dev python3.7-dev
```

(Note: At the time of writing, `python3-dev` was for Python 3.6. `python3.7-dev` is needed if you want to test against Python 3.7 locally.)

Before installing Aquarius's Python package requirements, it's recommended to create and activate a virtualenv (or equivalent).

At this point, an Elasticsearch database must already be running, now you can start the Aquarius server:

```bash
pip install -r requirements.txt
export FLASK_APP=aquarius/run.py
export CONFIG_FILE=config.ini
flask run
```

That will use HTTP (i.e. not SSL/TLS).

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

You can pass the configuration using the CONFIG_FILE environment variable (recommended) or locating your configuration in config.ini file.

In the configuration there are now two sections:

- oceandb: Contains different values to connect with oceandb. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- resources: In this section we are showing the url in which the aquarius is going to be deployed.

```yaml
[resources]
aquarius.url = http://localhost:5000
```

### Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

### New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

## License

Copyright 2020 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
