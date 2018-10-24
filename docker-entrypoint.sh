#!/bin/sh

export CONFIG_FILE=/aquarius/config.ini
envsubst < /aquarius/config.ini.template > /aquarius/config.ini
gunicorn -b ${AQUARIUS_URL#*://} -w ${AQUARIUS_WORKERS} aquarius.run:app
tail -f /dev/null
