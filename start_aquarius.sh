##
## Copyright 2023 Ocean Protocol Foundation
## SPDX-License-Identifier: Apache-2.0
##
export LOG_LEVEL=DEBUG
export FLASK_ENV=development
export FLASK_APP=aquarius/run.py
export AQUARIUS_URL=http://0.0.0.0
flask run --port=5000
