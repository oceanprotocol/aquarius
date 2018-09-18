#!/bin/sh

export CONFIG_FILE=/provider/oceandb.ini
envsubst < /provider/oceandb.ini.template > /provider/oceandb.ini
sleep 30

gunicorn -b ${PROVIDER_HOST}:${PROVIDER_PORT} -w ${PROVICER_WORKERS} provider.run:app
tail -f /dev/null
