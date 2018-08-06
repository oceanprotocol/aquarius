[![banner](docs/img/repo-banner@2x.png)](https://oceanprotocol.com)

<h1 align="center">provider-backend</h1>

> 💧 Provide an off-chain database store for data assets metadata and registration and perform part of access control in collaboration with the keeper-contracts.
> [oceanprotocol.com](https://oceanprotocol.com)

[![Build Status](https://travis-ci.com/oceanprotocol/provider-backend.svg?token=pA8zcB6SCxKW5MHpqs6L&branch=master)](https://travis-ci.com/oceanprotocol/provider-backend)


Get Started
------------

The most simple way to start is:

```bash
git clone git@github.com:oceanprotocol/provider-backend.git
cd provider-backend/

export FLASK_APP=provider_backend/run.py
export CONFIG_FILE=oceandb.ini 
flask run
```

Requirements
------------

You should have running a instance of BigchainDB and ganache-cli. 
You can start running the docker-compose in the docker directory:

```docker
docker-compose up
```

API documentation
-----------------
Once you have your application running you can access to the documentation in:

```bash
http://127.0.0.1:5000/api/v1/docs
```