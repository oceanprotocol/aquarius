#!/bin/sh

export CONFIG_FILE=/provider/config.ini
envsubst < /provider/config.ini.template > /provider/config.ini
gunicorn -b ${PROVIDER_URL#*://} -w ${PROVIDER_WORKERS} provider.run:app
tail -f /dev/null
