FROM python:3.6

MAINTAINER Ocean Protocol <devops@oceanprotocol.com>

ARG VERSION

COPY . /opt/provider-backend
WORKDIR /opt/provider-backend

RUN pip install flask
RUN pip install -r /opt/provider-backend/requirements_dev.txt --user
RUN chmod +x docker-entrypoint.sh

CMD "./docker-entrypoint.sh"

EXPOSE 5000
