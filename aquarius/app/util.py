#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("aquarius")


def sanitize_record(data_record):
    if "_id" in data_record:
        data_record.pop("_id")

    return json.dumps(data_record, default=datetime_converter)


def get_bool_env_value(envvar_name, default_value=0):
    assert default_value in (0, 1), "bad default value, must be either 0 or 1"
    try:
        return bool(int(os.getenv(envvar_name, default_value)))
    except Exception:
        return bool(default_value)


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()


def get_timestamp():
    """Return the current system timestamp."""
    return f"{datetime.utcnow().replace(microsecond=0).isoformat()}Z"
