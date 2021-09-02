#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

import configparser
import logging
import os

"""
This module defines values for database connection and other defaults.
"""
from aquarius.constants import ConfigSections

DEFAULT_NAME_AQUARIUS_URL = "http://localhost:5000"

NAME_AQUARIUS_URL = "aquarius.url"
ALLOW_FREE_ASSETS_ONLY = "allowFreeAssetsOnly"
MODULE = "module"
DB_HOSTNAME = "db.hostname"
DB_PORT = "db.port"

environ_names = {NAME_AQUARIUS_URL: ["AQUARIUS_BIND_URL", "Aquarius URL"]}

config_defaults = {
    ConfigSections.RESOURCES: {NAME_AQUARIUS_URL: DEFAULT_NAME_AQUARIUS_URL}
}


class Config(configparser.ConfigParser):
    def __init__(self, filename=None, **kwargs):
        """
        Reads the content of `filename` and sets the config values.
        """
        configparser.ConfigParser.__init__(self)

        self.read_dict(config_defaults)
        self._section_name = ConfigSections.RESOURCES
        self._es_name = ConfigSections.OCEANBD
        self._logger = kwargs.get("logger", logging.getLogger(__name__))
        self._logger.debug("Config: loading config file %s", filename)

        if filename:
            with open(filename) as fp:
                text = fp.read()
                self.read_string(text)
        else:
            if "text" in kwargs:
                self.read_string(kwargs["text"])
        self._load_environ()

    def _load_environ(self):
        for option_name, environ_item in environ_names.items():
            value = os.environ.get(environ_item[0])
            if value is not None:
                self._logger.debug(
                    "Config: setting environ %s = %s", option_name, value
                )
                self.set(self._section_name, option_name, value)

    @property
    def aquarius_url(self):
        return self.get(self._section_name, NAME_AQUARIUS_URL)

    @property
    def allow_free_assets_only(self):
        return self._section_name in self and self[self._section_name].get(
            ALLOW_FREE_ASSETS_ONLY, False
        )

    @property
    def db_url(self):
        """
        :return: Database url (hostname:port)
        """
        return (
            self.get(self._es_name, DB_HOSTNAME)
            + ":"
            + self.get(self._es_name, DB_PORT)
        )

    @property
    def module(self):
        return self.get(self._es_name, MODULE)

    # static methods

    @staticmethod
    def get_environ_help():
        result = []
        for option_name, environ_item in environ_names.items():
            # codacy fix
            assert option_name
            result.append("{:20}{:40}".format(environ_item[0], environ_item[1]))
        return "\n".join(result)
