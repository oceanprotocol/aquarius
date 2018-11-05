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
RUN pip install -e .

# config.ini configuration file variables
ENV DB_ENABLED='true'
ENV DB_MODULE='mongodb'
ENV DB_SECRET=''
ENV DB_SCHEME='http'
ENV DB_HOSTNAME='localhost'
ENV DB_PORT='27017'
ENV DB_APP_ID=''
ENV DB_APP_KEY=''
ENV DB_NAMESPACE='namespace'
ENV DB_NAME='aquarius'
ENV DB_COLLECTION='ddo'
ENV AQUARIUS_URL='http://0.0.0.0:5000'
# docker-entrypoint.sh configuration file variables
ENV AQUARIUS_WORKERS='1'

ENTRYPOINT ["/aquarius/docker-entrypoint.sh"]

EXPOSE 5000
