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


def get_schema_file(version, local=True):
    local_or_remote = "local" if local else "remote"
    suffix = "v4_0.json" if version == "v4" else "v0_6.json"
    path = (
        "ddo_checker/schemas/" + version + "/metadata_" + local_or_remote + "_" + suffix
    )

    local_schema_file = Path(pkg_resources.resource_filename("aquarius", path))
    assert local_schema_file.exists(), "Can't find schema file {}".format(
        local_schema_file
    )


def load_serial_data_file_path(file_path):
    file_path_obj = Path(file_path)
    assert Path(file_path_obj).exists(), "File path {} does not exist".format(file_path)

    assert file_path_obj.is_file()
    # file_name = file_path_obj.name

    if file_path_obj.suffix == ".json":
        with open(file_path_obj) as fp:
            json_dict = json.load(fp)
        return json_dict


def validator_file(schema_file):
    logging.info("Schema: {}".format(schema_file))
    this_json_schema_dict = load_serial_data_file_path(schema_file)
    return jschema.validators.Draft7Validator(this_json_schema_dict)


def validate_dict(this_json_dict, local=True):
    version = this_json_dict.get("version", "v3")
    schema_file = get_schema_file(version, local)
    validator = validator_file(schema_file)

    valid = validator.is_valid(this_json_dict)

    if valid:
        return True, []

    return False, list_errors(this_json_dict, schema_file=schema_file)


# %% Wrapper over jschema.Draft7Validator.iter_errors()
def list_errors(json_dict, schema_file):
    """Iterate over the validation errors, print to log.warn

    :param json_dict:
    :param schema_file:
    :return:
    """
    validator = validator_file(schema_file)

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
