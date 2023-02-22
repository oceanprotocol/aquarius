#!/bin/sh
##
## Copyright 2023 Ocean Protocol Foundation
## SPDX-License-Identifier: Apache-2.0
##

if [ "${DEPLOY_CONTRACTS}" = "true" ]; then
  while [ ! -f "/ocean-contracts/artifacts/ready" ]; do
    sleep 2
  done
fi


if [ ${RUN_EVENTS_MONITOR} = "1" ]; then
    /aquarius/start_events_monitor.sh &
fi

if [ ${RUN_AQUARIUS_SERVER} = "1" ]; then
    gunicorn -b ${AQUARIUS_BIND_URL#*://} --worker-tmp-dir /dev/shm --worker-class=gevent --worker-connections=1000 -w ${AQUARIUS_WORKERS} aquarius.run:app
fi
tail -f /dev/null
