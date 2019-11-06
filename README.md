[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Aquarius

> 🐋 Aquarius provides an off-chain database store for metadata about data assets.
> It's part of the [Ocean Protocol](https://oceanprotocol.com) software stack.

Note: Aquarius was formerly known as the Provider.

___"Aquarius is a constellation of the zodiac, situated between Capricornus and Pisces. Its name is Latin for "water-carrier" or "cup-carrier. Aquarius is one of the oldest of the recognized constellations along the zodiac (the Sun's apparent path)."___

[![Docker Build Status](https://img.shields.io/docker/build/oceanprotocol/aquarius.svg)](https://hub.docker.com/r/oceanprotocol/aquarius/) [![Travis (.com)](https://img.shields.io/travis/com/oceanprotocol/aquarius.svg)](https://travis-ci.com/oceanprotocol/aquarius) [![Codacy coverage](https://img.shields.io/codacy/coverage/10c8fddd5e8547c29de4906410a16ae7.svg)](https://app.codacy.com/project/ocean-protocol/aquarius/dashboard) [![PyPI](https://img.shields.io/pypi/v/ocean-aquarius.svg)](https://pypi.org/project/ocean-aquarius/) [![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/aquarius.svg)](https://github.com/oceanprotocol/aquarius/graphs/contributors)

---

**🐲🦑 THERE BE DRAGONS AND SQUIDS. This is in alpha state and you can expect running into problems. If you run into them, please open up [a new issue](https://github.com/oceanprotocol/aquarius/issues). 🦑🐲**

---

## For Aquarius Operators

If you're developing a marketplace, you'll want to run Aquarius and several other components locally, and the easiest way to do that is to use Barge. See the instructions in [the Barge repository](https://github.com/oceanprotocol/barge).

## For Aquarius API Users

The Ocean Protocol docs site has [documentation about the Aquarius API](https://docs.oceanprotocol.com/references/aquarius/). Note that it shows the docs for the version currently deployed with the Nile Testnet. To get documentation for other versions, there is a "past versions" link at the top of the page.

If you have Aquarius running locally, you can find API documentation at
[http://localhost:5000/api/v1/docs](http://localhost:5000/api/v1/docs) or maybe
[http://0.0.0.0:5000/api/v1/docs](http://0.0.0.0:5000/api/v1/docs).

Tip 1: If that doesn't work, then try `https`.

Tip 2: If your browser shows the Swagger header across the top but says "Failed to load spec." then we found that, in Chrome, if we went to `chrome://flags/#allow-insecure-localhost` and toggled it to Enabled, then relaunched Chrome, it worked.

If you want to know more about the ontology of the metadata, you can find all the information in
[OEP-8](https://github.com/oceanprotocol/OEPs/tree/master/8).

## For Aquarius Developers

### General Ocean Dev Docs

For information about Ocean's Python code style and related "meta" developer docs, see [the oceanprotocol/dev-ocean repository](https://github.com/oceanprotocol/dev-ocean).

### Running Locally, for Dev and Test

First, clone this repository:

```bash
git clone git@github.com:oceanprotocol/aquarius.git
cd aquarius/
```

Then run mongodb database that is a requirement for Aquarius. MongoDB can be installed directly using instructions from [official documentation](https://docs.mongodb.com/manual/installation/). Or if you have `docker` installed, you can run:

```bash
docker run -d -p 27017:27017 mongo
```

Note that it runs MongoDB but the Aquarius can also work with BigchainDB or Elasticsearch. If you want to run ElasticSearch or BigchainDB, update the file `config.ini` and run the Database engine with your preferred method.

Then install Aquarius's OS-level requirements:

```bash
sudo apt update
sudo apt install python3-dev python3.7-dev libssl-dev
```

(Note: At the time of writing, `python3-dev` was for Python 3.6. `python3.7-dev` is needed if you want to test against Python 3.7 locally. BigchainDB needs `libssl-dev`.)

Before installing Aquarius's Python package requirements, you should create and activate a virtualenv (or equivalent).

The most simple way to start is:

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
