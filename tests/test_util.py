#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os

import pytest

from aquarius.app.util import get_bool_env_value


def test_get_bool_env_value():
    name = "TEST_VAR"

    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 0) is False
    assert get_bool_env_value(name, 1) is True
    with pytest.raises(AssertionError):
        get_bool_env_value(name, "1")

    os.environ[name] = "0"
    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 1) is False
    assert get_bool_env_value(name, 0) is False
    os.environ[name] = "1"
    assert get_bool_env_value(name) is True
    assert get_bool_env_value(name, 0) is True
    assert get_bool_env_value(name, 1) is True
    os.environ[name] = "token"
    assert get_bool_env_value(name) is False
    assert get_bool_env_value(name, 0) is False
    assert get_bool_env_value(name, 1) is True
