#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

# %%
import json
import logging
from pathlib import Path

import jsonschema as jschema
import pkg_resources


def get_schema(version):
    base_version = "v3" if version.startswith("v3") else "v4"
    suffix = "v0_6.json" if base_version == "v3" else version + ".json"
    path = (
        "ddo_checker/schemas/" + base_version + "/metadata_remote_" + suffix
    )

    schema_file = Path(pkg_resources.resource_filename("aquarius", path))
    assert schema_file.exists(), "Can't find schema file {}".format(
        schema_file
    )

    logging.info("Schema: {}".format(schema_file))
    return load_serial_data_file_path(schema_file)


def load_serial_data_file_path(file_path):
    file_path_obj = Path(file_path)
    assert Path(file_path_obj).exists(), "File path {} does not exist".format(file_path)

    assert file_path_obj.is_file()
    # file_name = file_path_obj.name

    if file_path_obj.suffix == ".json":
        with open(file_path_obj) as fp:
            json_dict = json.load(fp)
        return json_dict


def validate_dict(this_json_dict):
    version = this_json_dict.get("version", "v3.0.0") if this_json_dict else "v3.0.0"

    schema = get_schema(version)
    validator = jschema.validators.Draft7Validator(schema)

    valid = validator.is_valid(this_json_dict)

    if valid:
        return True, []

    return False, list_errors(this_json_dict, schema=schema)


# %% Wrapper over jschema.Draft7Validator.iter_errors()
def list_errors(json_dict, schema):
    """Iterate over the validation errors, print to log.warn

    :param json_dict:
    :param schema_file:
    :return:
    """
    validator = jschema.validators.Draft7Validator(schema)

    # Build a list of 'errors', summarizing each
    errors = sorted(validator.iter_errors(json_dict), key=lambda e: e.path)
    error_summary = list()
    for i, err in enumerate(errors):
        # print("ERR",i)
        stack_path = list(err.relative_path)
        stack_path = [str(p) for p in stack_path]
        error_string = "Error {} at {}".format(i, "/".join(stack_path))
        # logging.warning("Error {} at {}".format(i, "/".join(stack_path)))
        # logging.warning("\t" + err.message)
        # error_summary.append(error_string)
        error_summary.append((error_string, err))
    return error_summary
