#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
import logging
import os
from collections import OrderedDict
from datetime import datetime

import dateutil.parser as parser

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATETIME_FORMAT_NO_Z = "%Y-%m-%dT%H:%M:%S"
ISO_DATETIME_FORMAT_NO_Z = "%Y-%m-%dT%H:%M:%S"

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
        return o.strftime(DATETIME_FORMAT)


def format_timestamp(timestamp):
    try:
        return f"{datetime.strptime(timestamp, DATETIME_FORMAT).replace(microsecond=0).isoformat()}Z"
    except Exception:
        return f"{datetime.strptime(timestamp, DATETIME_FORMAT_NO_Z).replace(microsecond=0).isoformat()}Z"


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
    _record["created"] = format_timestamp(
        datetime.fromtimestamp(timestamp).strftime(DATETIME_FORMAT)
    )
    _record["updated"] = _record["created"]

    # TODO: still needed?
    if "accessWhiteList" not in data:
        _record["accessWhiteList"] = []
    else:
        if not isinstance(data["accessWhiteList"], list):
            _record["accessWhiteList"] = []
        else:
            _record["accessWhiteList"] = data["accessWhiteList"]

    return _record


def validate_date_format(date):
    try:
        datetime.fromisoformat(date)
        return None, None
    except Exception as e:
        logging.error(f"validate_date_format: {str(e)}")
        return f"Incorrect data format, should be ISO Datetime Format", 400


def check_no_urls_in_files(services, method):
    for service in services:
        if "files" not in service:
            continue

        files = service["files"]["files"]
        for file_item in files:
            if "url" in file_item:
                logger.error("%s request failed: url is not allowed in files " % method)
                return "%s request failed: url is not allowed in files " % method, 400

    return None, None


def check_required_attributes(required_attributes, data, method):
    assert isinstance(
        data, dict
    ), "invalid `body` type, should already formatted into a dict."
    # logger.info("got %s request: %s" % (method, data))
    if not data:
        logger.error("%s request failed: data is empty." % method)
        return "payload seems empty.", 400

    keys = set(data.keys())
    if not isinstance(required_attributes, set):
        required_attributes = set(required_attributes)
    missing_attrs = required_attributes.difference(keys)
    if missing_attrs:
        logger.error(
            f"{method} request failed: required attributes {missing_attrs} are missing."
        )
        return f'"{missing_attrs}" are required in the call to {method}', 400

    return None, None


def list_errors(errors, data):
    error_list = list()
    for err in errors:
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        this_err_response = {"path": "/".join(stack_path), "message": err[1].message}
        error_list.append(this_err_response)
    return error_list


def validate_data(data, method):
    required_attributes = {
        "@context",
        "created",
        "id",
        "publicKey",
        "services",
        "dataToken",
    }

    msg, status = check_required_attributes(required_attributes, data, method)
    if msg:
        return msg, status

    msg, status = check_no_urls_in_files(data["services"], method)
    if msg:
        return msg, status

    msg, status = validate_date_format(data["created"])
    if status:
        return msg, status

    return None, None
