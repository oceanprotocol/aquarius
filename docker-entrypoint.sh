#!/bin/sh

export CONFIG_FILE=/aquarius/config.ini
envsubst < /aquarius/config.ini.template > /aquarius/config.ini

if [ ${RUN_EVENTS_MONITOR} = "true" ]; then
    /aquarius/start_events_monitor.sh &
fi

gunicorn -b ${AQUARIUS_URL#*://} -w ${AQUARIUS_WORKERS} aquarius.run:app
tail -f /dev/null
