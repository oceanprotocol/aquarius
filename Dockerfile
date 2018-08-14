FROM python:3.6-alpine

MAINTAINER Ocean Protocol <devops@oceanprotocol.com>

ARG VERSION

RUN apk add --update \
    python3 \
    python3-dev \
    py-pip \
    gcc \
    gmp gmp-dev \
    libffi-dev \
    openssl-dev \
    build-base \
  && pip install virtualenv \
  && rm -rf /var/cache/apk/*

COPY . provider-backend
WORKDIR provider-backend

RUN pip install -r requirements_dev.txt
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]

EXPOSE 5000
