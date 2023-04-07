##
## Copyright 2023 Ocean Protocol Foundation
## SPDX-License-Identifier: Apache-2.0
##
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

RUN python3.8 -m pip install -U pip==20.2.2
RUN pip install setuptools
RUN pip install wheel
RUN pip install .

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
RUN update-alternatives --set python3 /usr/bin/python3.8

ENV DB_MODULE='elasticsearch'
ENV DB_HOSTNAME='localhost'
ENV DB_PORT='27017'
#ELASTIC
ENV DB_INDEX='aquarius'
ENV AQUARIUS_BIND_URL='http://0.0.0.0:5000'
ENV ALLOW_FREE_ASSETS_ONLY='false'
# docker-entrypoint.sh configuration file variables
ENV AQUARIUS_WORKERS='8'
ENV EVENTS_ALLOW=''
ENV RUN_EVENTS_MONITOR='1'
#ENV ASSET_PURGATORY_URL="https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
#ENV ACCOUNT_PURGATORY_URL="https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json"
ENV PURGATORY_UPDATE_INTERVAL='60'
ENV RUN_AQUARIUS_SERVER='1'
ENV EVENTS_RPC='http://127.0.0.1:8545'
ENV EVENTS_MONITOR_SLEEP_TIME=30
ENV PRIVATE_KEY='0xc6914ea1e5ac6a1cd2107240be714735bf799ce9ea4125016aeb479266720ff4'
ENV BLOCKS_CHUNK_SIZE='5000'
ENV PROCESS_RETRY_QUEUE='1'
#ENV ADDRESS_FILE=''
#ENV ALLOWED_PUBLISHERS=['0x123','0x1234']
ENTRYPOINT ["/aquarius/docker-entrypoint.sh"]

EXPOSE 5000
