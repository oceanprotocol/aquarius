#!/bin/sh

export CONFIG_FILE=oceandb.ini
export FLASK_APP=provider/run.py
export FLASK_ENV=development

#sh ./scripts/deploy

sleep 30

#flask run --host=0.0.0.0
gunicorn -b 0.0.0.0:5000 -w 1 provider.run:app
tail -f /dev/null