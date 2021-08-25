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
    assert config.allow_free_assets_only is False


def test_config_from_env(monkeypatch):
    config_text = """
    [resources]
    aquarius.url = http://another-aqua.url
    """

    monkeypatch.setenv("AQUARIUS_BIND_URL", "test")
    config = Config(text=config_text)
    assert config.aquarius_url == "test"


def test_help():
    res = Config.get_environ_help()
    assert res.startswith("AQUARIUS_BIND_URL")
