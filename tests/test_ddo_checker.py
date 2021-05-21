#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

# from metadata_validator.json_versions import json4, json1
# from metadata_validator.schema_definitions import valid_schema
import copy

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft7Validator

from aquarius.ddo_checker import ddo_checker


# %%


def test_validator_simple():
    # A sample schema, like what we'd get from json.load()
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    # If no exception is raised by validate(), the instance is valid.
    validate(instance={"name": "Eggs"}, schema=schema)

    with pytest.raises(ValidationError) as e_info:
        validate(instance={"nnoname": "Eggs"}, schema=schema)
    print("Raised", e_info.value.message)

    with pytest.raises(ValidationError) as e_info:
        validate(instance={"name2": "Eggs"}, schema=schema)
    print("Raised", e_info.value.message)


# %%


def test_local_metadata_passes(schema_local_dict, sample_metadata_dict_local):
    validator = Draft7Validator(schema_local_dict)
    validator.validate(sample_metadata_dict_local)


def test_remote_metadata_passes(schema_remote_dict, sample_metadata_dict_remote):
    validator = Draft7Validator(schema_remote_dict)
    validator.validate(sample_metadata_dict_remote)


def test_fail_on_additonal_base_attribute(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_local["main"]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info

    sample_metadata_dict_remote["main"]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_additonal_file_attribute(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_local["main"]["files"][0]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info

    sample_metadata_dict_remote["main"]["files"][0]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_missing_file_index_attribute(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_local["main"]["files"][0]["index"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info

    del sample_metadata_dict_remote["main"]["files"][0]["index"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_missing_file_url_attribute(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_local["main"]["files"][0]["url"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info

    with pytest.raises(KeyError) as e_info:
        print(sample_metadata_dict_remote["main"]["files"][0]["url"])
        assert e_info


def test_fail_on_missing_main_attribute(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_local["main"]["name"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info

    del sample_metadata_dict_remote["main"]["name"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_allow_additional_information(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    more = {"more info": {"extra": "stuff", "item2": 2}}

    # delete additionalInformation, if present
    if "additionalInformation" in sample_metadata_dict_local:
        del sample_metadata_dict_local["additionalInformation"]
    validate(instance=sample_metadata_dict_local, schema=schema_local_dict)

    if "additionalInformation" in sample_metadata_dict_remote:
        del sample_metadata_dict_remote["additionalInformation"]
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    # add additional info
    sample_metadata_dict_local["additionalInformation"] = more
    validate(instance=sample_metadata_dict_local, schema=schema_local_dict)

    sample_metadata_dict_remote["additionalInformation"] = more
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_fail_local_missing_file_url(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_local["main"]["files"][0]["url"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_local, schema=schema_local_dict)
        assert e_info


def test_assert_remote_without_file_url(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    with pytest.raises(KeyError) as e_info:
        sample_metadata_dict_remote["main"]["files"][0]["url"]
        assert e_info


def test_validate_file(path_sample_metadata_local):
    ddo_checker.validate_file_local(path_sample_metadata_local)


def test_validate_dict(sample_metadata_dict_local):
    ddo_checker.validate_dict_local(sample_metadata_dict_local)


def test_is_valid_file(path_sample_metadata_local):
    assert ddo_checker.is_valid_file_local(path_sample_metadata_local)


def test_is_valid_dict(sample_metadata_dict_local):
    assert ddo_checker.is_valid_dict_local(sample_metadata_dict_local)


def test_list_errors_dict(sample_metadata_dict_local):
    assert len(ddo_checker.list_errors_dict_local(sample_metadata_dict_local)) == 0

    del sample_metadata_dict_local["main"]["name"]
    errors = ddo_checker.list_errors_dict_local(sample_metadata_dict_local)

    for i, err in enumerate(errors):
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        print("Error {} at {}: {}".format(i, "/".join(stack_path), err[1].message))

    assert 1 == len(errors)


def test_description_attr_regex_match(sample_metadata_dict_local):
    # Original metadata should have no problems
    errors = ddo_checker.list_errors_dict_local(sample_metadata_dict_local)
    assert [] == list(errors), "Should have no validation errors."

    # Modify description to include new lines, should also be valid.
    sample_metadata_dict_local["additionalInformation"][
        "description"
    ] = "multiline description. \n 2nd line. \n"
    errors = ddo_checker.list_errors_dict_local(sample_metadata_dict_local)
    assert [] == list(errors), "Should have no validation errors."


def test_algorithm_metadata_local(sample_algorithm_md_dict_local):
    errors = ddo_checker.list_errors_dict_local(sample_algorithm_md_dict_local)
    assert [] == list(errors), "Should have no validation errors."

    _copy = copy.deepcopy(sample_algorithm_md_dict_local)
    _copy["main"]["algorithm"].pop("container")
    errors = ddo_checker.list_errors_dict_local(_copy)
    assert 1 == len(errors), "Should have one validation error."

    _copy = copy.deepcopy(sample_algorithm_md_dict_local)
    _copy["main"]["algorithm"]["container"].pop("entrypoint")
    errors = ddo_checker.list_errors_dict_local(_copy)
    assert 1 == len(errors), "Should have one validation error."


def test_algorithm_metadata_remote(sample_algorithm_md_dict_remote):
    errors = ddo_checker.list_errors_dict_remote(sample_algorithm_md_dict_remote)
    assert [] == list(errors), "Should have no validation errors."

    _copy = copy.deepcopy(sample_algorithm_md_dict_remote)
    _copy["main"]["algorithm"].pop("container")
    errors = ddo_checker.list_errors_dict_remote(_copy)
    assert 1 == len(errors), "Should have one validation error."

    _copy = copy.deepcopy(sample_algorithm_md_dict_remote)
    _copy["main"]["algorithm"]["container"].pop("entrypoint")
    errors = ddo_checker.list_errors_dict_remote(_copy)
    assert 1 == len(errors), "Should have one validation error."


def test_status_present_empty(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {}
    errors = ddo_checker.list_errors_dict_remote(sample_metadata_dict_remote)
    assert 0 == len(errors), "Should be valid."
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_status_present_with_booleans(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isListed": True}
    errors = ddo_checker.list_errors_dict_remote(sample_metadata_dict_remote)
    assert 0 == len(errors), "Should be valid."
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_status_present_with_invalid_string(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isListed": "blabla"}
    errors = ddo_checker.list_errors_dict_remote(sample_metadata_dict_remote)
    assert 1 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert e_info.value.message == "'blabla' is not of type 'boolean'"


def test_status_present_with_two_invalid_strings(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {
        "isListed": "blabla",
        "isRetired": "bleble",
    }
    errors = ddo_checker.list_errors_dict_remote(sample_metadata_dict_remote)
    assert 2 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert e_info.value.message == "'blabla' is not of type 'boolean'"


def test_status_present_with_one_inadmissible_boolean(
    schema_local_dict,
    schema_remote_dict,
    sample_metadata_dict_local,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isSomethingElse": True}
    errors = ddo_checker.list_errors_dict_remote(sample_metadata_dict_remote)
    assert 1 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert (
        e_info.value.message
        == "Additional properties are not allowed ('isSomethingElse' was unexpected)"
    )
