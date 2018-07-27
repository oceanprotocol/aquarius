FROM python:3.6

MAINTAINER Ocean Protocol <devops@oceanprotocol.com>

ARG VERSION

COPY . /opt/provider-backend
WORKDIR /opt/provider-backend

RUN pip install -r /opt/provider-backend/requirements_dev.txt

ENV CONFIG_FILE=oceandb.ini
ENV FLASK_APP=provider_backend/run.py

RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD [""]

EXPOSE 5000
