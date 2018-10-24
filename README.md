[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Aquarius

> 🐋 Provide an off-chain database store for data assets metadata.
> [oceanprotocol.com](https://oceanprotocol.com)

___"Aquarius is a constellation of the zodiac, situated between Capricornus and Pisces. Its name is Latin for "water-carrier" or "cup-carrier", and its symbol is Aquarius.svg , a representation of water. Aquarius is one of the oldest of the recognized constellations along the zodiac (the Sun's apparent path)."___

[![Docker Build Status](https://img.shields.io/docker/build/oceanprotocol/aquarius.svg)](https://hub.docker.com/r/oceanprotocol/aquarius/) [![Travis (.com)](https://img.shields.io/travis/com/oceanprotocol/aquarius.svg)](https://travis-ci.com/oceanprotocol/aquarius) [![Codacy coverage](https://img.shields.io/codacy/coverage/0fa4c47049434406ad80932712f7ee6f.svg)](https://app.codacy.com/project/ocean-protocol/aquarius/dashboard) [![PyPI](https://img.shields.io/pypi/v/ocean-aquarius.svg)](https://pypi.org/project/ocean-aquarius/) [![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/aquarius.svg)](https://github.com/oceanprotocol/aquarius/graphs/contributors)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/aquarius/issues). 🦑🐲**

---

## Table of Contents

  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [API documentation](#api-documentation)
  - [Configuration](#configuration)
  - [Code style](#code-style)
  - [Testing](#testing)
  - [New Version](#new-version)
  - [License](#license)

---


## Features

Aquarius handles all non-blockchain related core functionality, including compute and storage interfaces, and connections to Ocean Keepers. Additionally, the Aquarius implements Ocean's Service Integrity and Orchestration capabilities, allowing for services to be requested, ordered, scheduled, verfied, and curated. 

## Running Locally, for Dev and Test

If you want to contribute to the development of the Aquarius, then you could do the following. (If you want to run a Aquarius in production, then you will have to do something else.)

First, clone this repository:

```bash
git clone git@github.com:oceanprotocol/aquarius.git
cd aquarius/
```

Then run some things that the Aquarius expects to be running:

```bash
cd docker
docker-compose up
```

You can see what that runs by reading [docker/docker-compose.yml](docker/docker-compose.yml).
Note that it runs MongoDB but the Aquarius can also work with BigchainDB or Elasticsearch.
It also runs [Ganache](https://github.com/trufflesuite/ganache) with all [Ocean Protocol Keeper Contracts](https://github.com/oceanprotocol/keeper-contracts) and [Ganache CLI](https://github.com/trufflesuite/ganache-cli).

The most simple way to start is:

```bash
pip install -r requirements_dev.txt # or requirements_conda.txt if using Conda
export FLASK_APP=aquarius/run.py
export CONFIG_FILE=config.ini
./scripts/deploy
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
aquarius
```

Then execute this command:

```bash
gunicorn --certfile cert.pem --keyfile key.pem -b 0.0.0.0:5000 -w 1 aquarius.run:app
```

## API documentation

Once you have your application running you can get access to the documentation at:

```bash
https://127.0.0.1:5000/api/v1/docs
```

(or `http` if you're using HTTP.)

Tip: if your browser shows the swagger header across the top but says "Failed to load spec." then we found that, in Chrome, if we went to chrome://flags/#allow-insecure-localhost and toggled it to Enabled, then relaunched Chrome, it worked.

If you want to know more about the ontology of the metadata, you can find all the information in
[OEP-8](https://github.com/oceanprotocol/OEPs/tree/master/8).

## Configuration

You can pass the configuration using the CONFIG_FILE environment variable (recommended) or locating your configuration in config.ini file.

In the configuration there are now two sections:

- oceandb: Contains different values to connect with oceandb. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- resources: In this section we are showing the url in wich the aquarius is going to be deployed.

    ```yaml
    [resources]
    aquarius.url = http://localhost:5000
    ```
    

## Code style

The information about code style in python is documented in this two links [python-developer-guide](https://github.com/oceanprotocol/dev-ocean/blob/master/doc/development/python-developer-guide.md)
and [python-style-guide](https://github.com/oceanprotocol/dev-ocean/blob/master/doc/development/python-style-guide.md).
    
## Testing

Automatic tests are setup via Travis, executing `tox`.
Our test use pytest framework.

## New Version

The `bumpversion.sh` script helps to bump the project version. You can execute the script using as first argument {major|minor|patch} to bump accordingly the version.

## License

```
Copyright 2018 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
