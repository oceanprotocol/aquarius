#!/bin/bash
export CONFIG_FILE=oceandb.ini
export FLASK_APP=provider_backend/run.py
export FLASK_ENV=development
flask run
tail -f /dev/null