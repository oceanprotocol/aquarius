[![banner](docs/img/repo-banner@2x.png)](https://oceanprotocol.com)

<h1 align="center">provider</h1>

> 🐋 Provide an off-chain database store for data assets metadata and registration and perform part of access control in collaboration with the keeper-contracts.
> [oceanprotocol.com](https://oceanprotocol.com)

[![Build Status](https://travis-ci.com/oceanprotocol/provider.svg?token=pA8zcB6SCxKW5MHpqs6L&branch=master)](https://travis-ci.com/oceanprotocol/provider)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/provider/issues). 🦑🐲**

---


Get Started
------------

The most simple way to start is:

```bash
git clone git@github.com:oceanprotocol/provider.git
cd provider/

export FLASK_APP=provider/run.py
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

Configuration
-------------

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
