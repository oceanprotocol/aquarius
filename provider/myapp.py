import logging
import os
import sys

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

if 'CONFIG_FILE' in os.environ and os.environ['CONFIG_FILE']:
    app.config['CONFIG_FILE'] = os.environ['CONFIG_FILE']
else:
    try:
        app.config['CONFIG_FILE'] = 'config.ini'
    except Exception as e:
        logging.error('A config file must be set in the environment variable "CONFIG_FILE" or in config.ini')
        logging.error(e)
        sys.exit(1)
