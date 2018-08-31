[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# provider

> 🐋 Provide an off-chain database store for data assets metadata and registration and perform part of access control in collaboration with the keeper-contracts.
> [oceanprotocol.com](https://oceanprotocol.com)

[![Travis (.com)](https://img.shields.io/travis/com/oceanprotocol/provider.svg)](https://travis-ci.com/oceanprotocol/provider)
[![Codacy coverage](https://img.shields.io/codacy/coverage/0fa4c47049434406ad80932712f7ee6f.svg)](https://app.codacy.com/project/ocean-protocol/provider/dashboard)
[![PyPI](https://img.shields.io/pypi/v/ocean-provider.svg)](https://pypi.org/project/ocean-provider/)
[![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/provider.svg)](https://github.com/oceanprotocol/provider/graphs/contributors)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/provider/issues). 🦑🐲**

---

## Table of Contents

  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [API documentation](#api-documentation)
  - [Configuration](#configuration)
  - [Code style](#code-style)
  - [Testing](#testing)
  - [New version](#version)
  - [License](#license)

---


## Features

The Provider handles all non-blockchain related core functionality, including compute and storage interfaces, and connections to Ocean Keepers. Additionally, the Provider implements Ocean's Service Integrity and Orchestration capabilities, allowing for services to be requested, ordered, scheduled, verfied, and curated. 

## Prerequisites

You should have running a instance of BigchainDB and ganache-cli. 
You can start running the docker-compose in the docker directory:

```docker
docker-compose up
```

## Quick Start

The most simple way to start is (not for production):

```bash
git clone git@github.com:oceanprotocol/provider.git
cd provider/

export FLASK_APP=provider/run.py
export CONFIG_FILE=oceandb.ini 
flask run
```

The proper way to run the flask application is using a application server as gunicorn. This allow you to run using SSL, 
you only need to generate your certificates and execute this command: 

```bash
gunicorn --certfile cert.pem --keyfile key.pem -b 0.0.0.0:5000 -w 1 provider.run:app
```

Be aware of add in the config file how you want to resolve your server:
    
```yaml
provider.scheme = https
provider.host = localhost
provider.port = 5000
```

You can genereta some certificates for testing running:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

## API documentation

Once you have your application running you can access to the documentation in:

```bash
http://127.0.0.1:5000/api/v1/docs
```

## Configuration


In the configuration there are now three sections:

- oceandb: Contains different values to connect with oceandb. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- keeper-contracts: This section help you to connect with the network where you have deployed the contracts.
    ```yaml
    [keeper-contracts]
    keeper.host=0.0.0.0
    keeper.port=8545
    #contracts.folder=venv/contracts
    market.address=0xbc0be3598a31715bac5235718f96bb242804e61e
    auth.address=0x6ba5f72e5399aa67db5b22ee791851937d4910f5
    token.address=0xfd83b273b395b1029c41bb32071500bf662e6a8a
    provider.address=
    ```
- resources: This section have properties to connect with the different resourcer provideres. At the moment we are only using Azure but this is going to increase quickly.
    ```yaml
    [resources]
    azure.account.name=testocnfiles
    azure.account.key=k2Vk4yfb88WNlWW+W54a8ytJm8MYO1GW9IgiV7TNGKSdmKyVNXzyhiRZ3U1OHRotj/vTYdhJj+ho30HPyJpuYQ==
    azure.container=testfiles
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
