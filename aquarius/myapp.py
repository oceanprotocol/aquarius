#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
"""
This module creates an instance of flask `app` and sets the environment configuration.
If `AQUARIUS_CONFIG_FILE` is not found in environment variables, default `config.ini` file is used.
"""
import logging
import os

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

if "AQUARIUS_CONFIG_FILE" in os.environ and os.environ["AQUARIUS_CONFIG_FILE"]:
    app.config["AQUARIUS_CONFIG_FILE"] = os.environ["AQUARIUS_CONFIG_FILE"]
else:
    logging.info("Using default config: config.ini")
    app.config["AQUARIUS_CONFIG_FILE"] = "config.ini"
