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

from tests.ddos.ddo_sample1_v4 import json_dict


def test_remote_metadata_passes(schema_remote_dict_v4):
    validator = Draft7Validator(schema_remote_dict_v4)
    validator.validate(json_dict)
