#!/bin/sh

export CONFIG_FILE=/aquarius/config.ini
envsubst < /aquarius/config.ini.template > /aquarius/config.ini

if [ "${DEPLOY_CONTRACTS}" = "true" ]; then
  while [ ! -f "/ocean-contracts/artifacts/ready" ]; do
    sleep 2
  done
fi


if [ ${RUN_EVENTS_MONITOR} = "1" ]; then
    /aquarius/start_events_monitor.sh &
fi

gunicorn -b ${AQUARIUS_URL#*://} --worker-tmp-dir /dev/shm --worker-class=gevent --worker-connections=1000 -w ${AQUARIUS_WORKERS} aquarius.run:app
tail -f /dev/null
