from flask import Flask
from flask_cors import CORS
import os
import sys
import logging

app = Flask(__name__)
CORS(app)

if 'CONFIG_FILE' in os.environ and os.environ['CONFIG_FILE']:
    app.config['CONFIG_FILE'] = os.environ['CONFIG_FILE']
else:
    logging.error('A config file must be set in the environment variable "CONFIG_FILE".')
    sys.exit(1)
