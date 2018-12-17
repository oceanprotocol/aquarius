# Aquarius Documentation for Aquarius Developers

This documentation is for someone who wants to work on the Aquarius code itself, i.e. the code in the [oceanprotocol/aquarius repository](https://github.com/oceanprotocol/aquarius).

## General Ocean Dev Docs

For information about Ocean's Python code style and related "meta" developer docs, see [the oceanprotocol/dev-ocean repository](https://github.com/oceanprotocol/dev-ocean).

## Running Locally, for Dev and Test

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

## Configuration

You can pass the configuration using the CONFIG_FILE environment variable (recommended) or locating your configuration in config.ini file.

In the configuration there are now two sections:

- oceandb: Contains different values to connect with oceandb. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- resources: In this section we are showing the url in wich the aquarius is going to be deployed.

    ```yaml
    [resources]
    aquarius.url = http://localhost:5000
    ```

## Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

## New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.
