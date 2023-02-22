#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
"""
This module creates an instance of flask `app`.
"""
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
