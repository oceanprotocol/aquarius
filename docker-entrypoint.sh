#!/bin/bash
export CONFIG_FILE=oceandb.ini
export FLASK_APP=provider_backend/run.py
"$(flask run)"
tail -f /dev/null