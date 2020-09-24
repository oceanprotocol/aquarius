FROM python:3.6-alpine
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

ARG VERSION

RUN apk add --no-cache --update\
    build-base \
    gcc \
    gettext\
    gmp \
    gmp-dev \
    libffi-dev \
    openssl-dev \
    py-pip \
    python3 \
    python3-dev \
  && pip install virtualenv

COPY . /aquarius
WORKDIR /aquarius

# Only install install_requirements, not dev_ or test_requirements
RUN pip install .

# config.ini configuration file variables
ENV DB_MODULE='mongodb'
ENV DB_HOSTNAME='localhost'
ENV DB_PORT='27017'
#MONGO
ENV DB_NAME='aquarius'
ENV DB_COLLECTION='ddo'
#ELASTIC
ENV DB_INDEX='aquarius'
#BDB
ENV DB_SECRET=''
ENV DB_SCHEME='http'
ENV DB_NAMESPACE='namespace'
ENV AQUARIUS_URL='http://0.0.0.0:5000'
ENV ALLOW_FREE_ASSETS_ONLY='false'
ENV RATING_ALLOWED_UPDATER=''
# docker-entrypoint.sh configuration file variables
ENV AQUARIUS_WORKERS='1'
ENV EVENTS_ALLOW=''
ENV RUN_EVENTS_MONITOR=''
ENV EVENTS_RPC='http://127.0.0.1:8545'
ENV EVENTS_ECIES_PRIVATE_KEY='0xc6914ea1e5ac6a1cd2107240be714735bf799ce9ea4125016aeb479266720ff4'
ENV ARTIFACTS_PATH=''
ENV ADDRESS_FILE=''
ENTRYPOINT ["/aquarius/docker-entrypoint.sh"]

EXPOSE 5000
