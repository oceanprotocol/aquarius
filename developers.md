# Aquarius development

  * [Running Aquarius locally, for development and testing](#running-aquarius-locally-for-development-and-testing)
  * [General Ocean Dev Docs](#general-ocean-dev-docs)
  * [Configuration](#configuration)
  * [Extras: Testing &amp; Versioning](#extras-testing--versioning)
  * [Ensuring changes are well propagated](#ensuring-changes-are-well-propagated)
     
## Running Aquarius locally, for development and testing

The easiest way is through [Barge](https://github.com/oceanprotocol/barge). Run a Barge instance without Aquarius.

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
pip install wheel
pip install -r requirements.txt
```

Now you are free to configure your own special Aquarius, and fiddle with the EventsMonitor, which you can run using `python3 events-monitor-main.py`. At this point, with the Elasticsearch database already running, now you can also start the Aquarius API server:

```bash
export FLASK_APP=aquarius/run.py
export AQUARIUS_CONFIG_FILE=config.ini
flask run --port=5000
```

That will use HTTP (i.e. not SSL/TLS). You can now use the API on `http://localhost:5000`

⚠️ ATTENTION: if you are using an Aquarius search endpoint and it returns more than 10k results,
    Elasticsearch will throw a TransportError and your query will fail. If your error message seems related to the results limitation, please try to refine your search.
    The solution is to be more specific in your search. This can happpen on test networks with many assets, like rinkeby.

If you want to contribute to Aquarius, you are welcome to do so. We are always excited to see Aquarius improve and grow, and to get the community involved in its development. We ask you just one tiny thing: Make sure you install the pre-commit hooks using the command `pre-commit install`. This will make sure your imports are sorted and your code is properly formatted before committing.

By the way... The proper way to run the Flask application, in a more "production-y" environment, is by using an application server such as Gunicorn. This allow you to run using SSL/TLS.
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

## General Ocean Dev Docs

Ocean's Python code style and related "meta" developer docs are at [oceanprotocol/dev-ocean repo](https://github.com/oceanprotocol/dev-ocean).

## Configuration

You can pass the configuration using the `AQUARIUS_CONFIG_FILE` environment variable (recommended) or locating your configuration in config.ini file.

In the configuration there are now two sections:

- oceandb: Contains different values to connect with elasticsearch. You can find more information about how to use OceanDB [here](https://github.com/oceanprotocol/oceandb-driver-interface).
- resources: In this section we are showing the url in which the aquarius is going to be deployed.

```yaml
[resources]
aquarius.url = http://localhost:5000
```

## Extras: Testing & Versioning

Automatic tests are set up via Travis, executing `tox`. Our tests use the pytest framework.

If you want to run a test individually, without using tox, run `pytest test_file_path.py::test_specific_test`.
In this case, if some environment variables are not set, pytest will default to those defined in `pytest.ini` (defined in the project root directory). These variables are the same as the ones tox.ini defines.

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

### Ensuring changes are well propagated

Changes to Aquarius have ripple effects to this repo's docker image, and barge. 

When you make changes, you have to make sure that you're not breaking downstream components that use this. Kindly make sure that you consider all ripple effects.

You may need to:
- update this repo
- update this repo's docker container (if needed)
- update barge with this repo's changes (if needed)

All changes should double-check that Ocean Market still works as expected.
- test Ocean Market locally, focusing on where the change was made. This will hit the API endpoint. [Ocean.py marketplace flow](https://github.com/oceanprotocol/ocean.py/blob/main/READMEs/marketplace-flow.md) shows how to spin it up locally in a Python context
- test Ocean Market on rinkeby or ropsten
