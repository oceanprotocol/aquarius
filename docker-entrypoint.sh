#!/bin/sh

export CONFIG_FILE=/provider/oceandb.ini
envsubst < /provider/oceandb.ini.template > /provider/oceandb.ini
echo "Waiting for contracts to be generated..."
while [ ! -f "/usr/local/contracts/ready" ]; do
  sleep 2
done
gunicorn -b ${PROVIDER_HOST}:${PROVIDER_PORT} -w ${PROVICER_WORKERS} provider.run:app
tail -f /dev/null
