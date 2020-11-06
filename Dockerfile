FROM ubuntu:18.04
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

ARG VERSION
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    gcc \
    python3.8 \
    python3-pip \
    python3.8-dev \
    gettext-base

COPY . /aquarius
WORKDIR /aquarius

RUN python3.8 -m pip install -U pip
RUN pip install setuptools
RUN pip install wheel
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
# docker-entrypoint.sh configuration file variables
ENV AQUARIUS_WORKERS='8'
ENV EVENTS_ALLOW=''
ENV RUN_EVENTS_MONITOR=''
ENV EVENTS_RPC='http://127.0.0.1:8545'
ENV EVENTS_ECIES_PRIVATE_KEY='0xc6914ea1e5ac6a1cd2107240be714735bf799ce9ea4125016aeb479266720ff4'
#ENV ARTIFACTS_PATH=''
#ENV ADDRESS_FILE=''
#ENV ALLOWED_PUBLISHERS=['0x123','0x1234']
ENTRYPOINT ["/aquarius/docker-entrypoint.sh"]

EXPOSE 5000
