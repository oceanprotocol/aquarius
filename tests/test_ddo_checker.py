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

from aquarius.ddo_checker.ddo_checker import validate_dict


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


def test_remote_metadata_passes(schema_remote_dict, sample_metadata_dict_remote):
    validator = Draft7Validator(schema_remote_dict)
    validator.validate(sample_metadata_dict_remote)


def test_fail_on_additonal_base_attribute(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["main"]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_additonal_file_attribute(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["main"]["files"][0]["EXTRA ATTRIB!"] = 0
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_missing_file_index_attribute(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_remote["main"]["files"][0]["index"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_fail_on_missing_file_url_attribute(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    with pytest.raises(KeyError) as e_info:
        print(sample_metadata_dict_remote["main"]["files"][0]["url"])
        assert e_info


def test_fail_on_missing_main_attribute(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    del sample_metadata_dict_remote["main"]["name"]
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)
        assert e_info


def test_allow_additional_information(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    more = {"more info": {"extra": "stuff", "item2": 2}}

    if "additionalInformation" in sample_metadata_dict_remote:
        del sample_metadata_dict_remote["additionalInformation"]
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    sample_metadata_dict_remote["additionalInformation"] = more
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_assert_remote_without_file_url(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    with pytest.raises(KeyError) as e_info:
        sample_metadata_dict_remote["main"]["files"][0]["url"]
        assert e_info


def test_validate_dict(sample_metadata_dict_remote):
    valid, _ = validate_dict(sample_metadata_dict_remote)
    assert valid


def test_list_errors_dict(sample_metadata_dict_remote):
    valid, errors = validate_dict(sample_metadata_dict_remote)
    assert len(errors) == 0

    del sample_metadata_dict_remote["main"]["name"]
    _, errors = validate_dict(sample_metadata_dict_remote)

    for i, err in enumerate(errors):
        stack_path = list(err[1].relative_path)
        stack_path = [str(p) for p in stack_path]
        print("Error {} at {}: {}".format(i, "/".join(stack_path), err[1].message))

    assert 1 == len(errors)


def test_description_attr_regex_match(sample_metadata_dict_remote):
    # Original metadata should have no problems
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert [] == list(errors), "Should have no validation errors."

    # Modify description to include new lines, should also be valid.
    sample_metadata_dict_remote["additionalInformation"][
        "description"
    ] = "multiline description. \n 2nd line. \n"

    _, errors = validate_dict(sample_metadata_dict_remote)
    assert [] == list(errors), "Should have no validation errors."


def test_algorithm_metadata_remote(sample_algorithm_md_dict_remote):
    _, errors = validate_dict(sample_algorithm_md_dict_remote)
    assert [] == list(errors), "Should have no validation errors."

    _copy = copy.deepcopy(sample_algorithm_md_dict_remote)
    _copy["main"]["algorithm"].pop("container")
    _, errors = validate_dict(_copy)
    assert 1 == len(errors), "Should have one validation error."

    _copy = copy.deepcopy(sample_algorithm_md_dict_remote)
    _copy["main"]["algorithm"]["container"].pop("entrypoint")
    _, errors = validate_dict(_copy)
    assert 1 == len(errors), "Should have one validation error."


def test_status_present_empty(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {}
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert 0 == len(errors), "Should be valid."
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_status_present_with_booleans(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isListed": True}
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert 0 == len(errors), "Should be valid."
    validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)


def test_status_present_with_invalid_string(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isListed": "blabla"}
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert 1 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert e_info.value.message == "'blabla' is not of type 'boolean'"


def test_status_present_with_two_invalid_strings(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {
        "isListed": "blabla",
        "isRetired": "bleble",
    }
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert 2 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert e_info.value.message == "'blabla' is not of type 'boolean'"


def test_status_present_with_one_inadmissible_boolean(
    schema_remote_dict,
    sample_metadata_dict_remote,
):
    sample_metadata_dict_remote["status"] = {"isSomethingElse": True}
    _, errors = validate_dict(sample_metadata_dict_remote)
    assert 1 == len(errors), "Should be invalid."
    with pytest.raises(ValidationError) as e_info:
        validate(instance=sample_metadata_dict_remote, schema=schema_remote_dict)

    assert (
        e_info.value.message
        == "Additional properties are not allowed ('isSomethingElse' was unexpected)"
    )
