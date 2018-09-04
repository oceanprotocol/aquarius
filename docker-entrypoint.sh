#!/bin/sh

export CONFIG_FILE=oceandb.ini

sleep 30

gunicorn -b 0.0.0.0:5000 -w 1 provider.run:app
tail -f /dev/null