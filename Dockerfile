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

COPY . /provider
WORKDIR /provider

RUN pip install -r requirements_dev.txt

# oceandb.ini configuration file variables
ENV DB_ENABLED='true'
ENV DB_MODULE='mongodb'
ENV DB_SECRET=''
ENV DB_SCHEME='http'
ENV DB_HOSTNAME='localhost'
ENV DB_PORT='27017'
ENV DB_APP_ID=''
ENV DB_APP_KEY=''
ENV DB_NAMESPACE='namespace'
ENV DB_NAME='test'
ENV DB_COLLECTION='protokeeper'
ENV KEEPER_URL='http://127.0.0.1:8548'
ENV KEEPER_NETWORK='development'
#ENV MARKET_ADDRESS=''
#ENV AUTH_ADDRESS=''
#ENV TOKEN_ADDRESS=''
ENV PROVIDER_ADDRESS=''
ENV AZURE_ACCOUNT_NAME='testocnfiles'
ENV AZURE_ACCOUNT_KEY='k2Vk4yfb88WNlWW+W54a8ytJm8MYO1GW9IgiV7TNGKSdmKyVNXzyhiRZ3U1OHRotj/vTYdhJj+ho30HPyJpuYQ=='
ENV AZURE_CONTAINER='testfiles'
ENV PROVIDER_URL='http://0.0.0.0:5000'
# docker-entrypoint.sh configuration file variables
ENV PROVICER_WORKERS='1'

ENTRYPOINT ["/provider/docker-entrypoint.sh"]

EXPOSE 5000
