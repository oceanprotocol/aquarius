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

# %%
# Here is the Schema file, loaded as the default to validate against
LOCAL_SCHEMA_FILE = Path(
    pkg_resources.resource_filename(
        "aquarius", "ddo_checker/schemas/metadata_local_v0_6.json"
    )
)
assert LOCAL_SCHEMA_FILE.exists(), "Can't find schema file {}".format(LOCAL_SCHEMA_FILE)
REMOTE_SCHEMA_FILE = Path(
    pkg_resources.resource_filename(
        "aquarius", "ddo_checker/schemas/metadata_remote_v0_6.json"
    )
)
assert LOCAL_SCHEMA_FILE.exists(), "Can't find schema file {}".format(
    REMOTE_SCHEMA_FILE
)


# TODO: Handle full file path vs. dictionary better?


# %%
def load_serial_data_file_path(file_path):
    file_path_obj = Path(file_path)
    assert Path(file_path_obj).exists(), "File path {} does not exist".format(file_path)

    assert file_path_obj.is_file()
    # file_name = file_path_obj.name

    if file_path_obj.suffix == ".json":
        with open(file_path_obj) as fp:
            json_dict = json.load(fp)
        return json_dict

    # TODO: Add Yaml parser

    # if file_path_obj.suffix in ['.yaml', '.yml']:
    #     with open(file_path_obj) as fp:
    #         json_dict = json.load(fp)
    #     return json_dict


# %%


def validator_file(schema_file):
    logging.info("Schema: {}".format(schema_file))
    this_json_schema_dict = load_serial_data_file_path(schema_file)
    return jschema.validators.Draft7Validator(this_json_schema_dict)


def validator_dict(schema_dict):
    return jschema.validators.Draft7Validator(schema_dict)


# %% Wrapper over jschema.Draft7Validator.validate()


def validate_dict(this_json_dict, schema_file):
    validator = validator_file(schema_file)
    return validator.validate(this_json_dict)


# Convenience function, load into dictionary first
def validate_file(json_file_abs_path, schema_file):
    this_json_dict = load_serial_data_file_path(json_file_abs_path)
    return validate_dict(this_json_dict, schema_file)


# Convenience functions
def validate_file_local(json_file_abs_path):
    return validate_file(json_file_abs_path, LOCAL_SCHEMA_FILE)


def validate_file_remote(json_file_abs_path):
    return validate_file(json_file_abs_path, REMOTE_SCHEMA_FILE)


def validate_dict_local(this_json_dict):
    return validate_dict(this_json_dict, LOCAL_SCHEMA_FILE)


def validate_dict_remote(this_json_dict):
    return validate_dict(this_json_dict, REMOTE_SCHEMA_FILE)


# %%
# Wrapper over jschema.Draft7Validator.is_valid()


def is_valid_file(json_file_abs_path, schema_file):
    validator = validator_file(schema_file)
    this_json_dict = load_serial_data_file_path(json_file_abs_path)
    return validator.is_valid(this_json_dict)


def is_valid_dict(this_json_dict, schema_file=LOCAL_SCHEMA_FILE):
    validator = validator_file(schema_file)
    return validator.is_valid(this_json_dict)


# Convenience functions
def is_valid_file_local(json_file_abs_path):
    return is_valid_file(json_file_abs_path, LOCAL_SCHEMA_FILE)


def is_valid_file_remote(json_file_abs_path):
    return is_valid_file(json_file_abs_path, REMOTE_SCHEMA_FILE)


def is_valid_dict_local(this_json_dict):
    return is_valid_dict(this_json_dict, schema_file=LOCAL_SCHEMA_FILE)


def is_valid_dict_remote(this_json_dict):
    return is_valid_dict(this_json_dict, schema_file=REMOTE_SCHEMA_FILE)


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


# Convenience functions
def list_errors_file_local(json_file_abs_path):
    this_json_dict = load_serial_data_file_path(json_file_abs_path)
    return list_errors(this_json_dict, LOCAL_SCHEMA_FILE)


def list_errors_file_remote(json_file_abs_path):
    this_json_dict = load_serial_data_file_path(json_file_abs_path)
    return list_errors(this_json_dict, REMOTE_SCHEMA_FILE)


def list_errors_dict_local(this_json_dict):
    return list_errors(this_json_dict, LOCAL_SCHEMA_FILE)


def list_errors_dict_remote(this_json_dict):
    return list_errors(this_json_dict, REMOTE_SCHEMA_FILE)
