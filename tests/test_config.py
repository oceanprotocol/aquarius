#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from aquarius.config import Config


def test_config_from_text():
    config_text = """
    [resources]
    aquarius.url = http://another-aqua.url
    """

    config = Config(text=config_text)
    assert config.aquarius_url == "http://another-aqua.url"


def test_help():
    res = Config.get_environ_help()
    assert res.startswith("AQUARIUS_BIND_URL")
