#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
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


def get_main_metadata(services):
    metadata = get_metadata_from_services(services)
    assert "main" in metadata, "metadata is missing the `main` section."
    return metadata["main"]


def get_metadata_from_services(services):
    if not services:
        return None

    for service in services:
        if service["type"] == "metadata":
            assert (
                "attributes" in service
            ), "metadata service is missing the `attributes` section."
            return service["attributes"]


def init_new_ddo(data, timestamp):
    _record = copy.deepcopy(data)
    _record["created"] = datetime.now().isoformat()
    _record["updated"] = _record["created"]

    return _record


def list_errors(errors, data):
    error_list = list()
    for err in errors:
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        this_err_response = {"path": "/".join(stack_path), "message": err[1].message}
        error_list.append(this_err_response)
    return error_list
