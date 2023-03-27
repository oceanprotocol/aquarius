# Aquarius development

  * [Running Aquarius locally, for development and testing](#running-aquarius-locally-for-development-and-testing)
  * [General Ocean Dev Docs](#general-ocean-dev-docs)
  * [Extras: Testing &amp; Versioning](#extras-testing--versioning)
  * [Ensuring changes are well propagated](#ensuring-changes-are-well-propagated)

## Running Aquarius locally, for development and testing

The easiest way is through [Barge](https://github.com/oceanprotocol/barge). Run a Barge instance without Aquarius and with RBAC Server.

```bash
git clone https://github.com/oceanprotocol/barge
cd barge
./start_ocean.sh  --no-aquarius --with-rbac
```

#### Running Elasticsearch
There are two ways of running Elasticsearch. The first one is to run it bare-bones.
In a new terminal tab, run the elasticsearch database (required for Aquarius).
You can also run this in the background, but it helps development to see all output separately.

The following snippet downloads and runs Elasticsearch 8.5.1 for a Linux x86 machine, but this can differ per your setup.
Make sure you adjust the file names and download links if needed.

```bash
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.5.1-linux-x86_64.tar.gz
tar -xzf elasticsearch-8.5.1-linux-x86_64.tar.gz
./elasticsearch-8.5.1/bin/elasticsearch
```

Don't forget to change the automatically set password:

```bash
./elasticsearch-8.5.1/bin/elasticsearch-reset-password -i -u elastic --url https://localhost:9200
```

Alternately, you can run Elasticsearch from docker:
`docker run --rm -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e ELASTIC_PASSWORD=<your_password> elasticsearch:7.14.2`

The arguments have the following meaning:
- `--rm` Automatically remove the container when it exits
- `-p 9200:9200 -p 9300:9300` expose ports 9200 and 9300 and bind them.
- `-e "discovery.type=single-node"` sets the environment variable for Elasticsearch. If `discovery.type` is set to `single-node`, Elasticsearch forms a single-node cluster. Thus, our node will elect itself master and will not join a cluster with any other node. Since we are not building a multiple-node cluster, we are settings this to `single-node`.
- `-e ELASTIC_PASSWORD=<your_password>` sets the password for Elasticsearch.

After spinning up Elasticsearch using either method, you can continue with the following Aquarius instructions. In yet another tab, clone this repository:

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

Then export the env var so that:

```yaml
export AQUARIUS_URL=http://localhost:5000
```

Then execute this command:

```bash
gunicorn --certfile cert.pem --keyfile key.pem -b 0.0.0.0:5000 -w 1 aquarius.run:app
```

## General Ocean Dev Docs

Ocean's Python code style and related "meta" developer docs are at [oceanprotocol/dev-ocean repo](https://github.com/oceanprotocol/dev-ocean).

## Extras: Testing & Versioning

Automatic tests are set up via GitHub Actions. Our tests use the pytest framework.

If you want to run a test individually, run `pytest test_file_path.py::test_specific_test`.
In this case, if some environment variables are not set, pytest will default to those defined in `pytest.ini` (defined in the project root directory).

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

## Force setting the last processed block
Use the registered flask command with `chain_id` and `block_number` parameters:

```bash
export FLASK_APP=aquarius/run.py
flask force_set_block 8996 12
```
