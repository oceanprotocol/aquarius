#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import pytest

from aquarius.app.cached_block import update_cached_block


def test_update_cached_block_failure():
    with pytest.raises(Exception) as err:
        update_cached_block(None)
    assert err.value.args[0] == "Cached block is None."
