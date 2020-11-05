#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import configparser
import logging
import os

from aquarius.constants import ConfigSections

DEFAULT_NAME_AQUARIUS_URL = 'http://localhost:5000'

NAME_AQUARIUS_URL = 'aquarius.url'
ALLOW_FREE_ASSETS_ONLY = 'allowFreeAssetsOnly'
MODULE = 'module'
DB_HOSTNAME = 'db.hostname'
DB_PORT = 'db.port'

environ_names = {
    NAME_AQUARIUS_URL: ['AQUARIUS_URL', 'Aquarius URL'],
}

config_defaults = {
    ConfigSections.RESOURCES: {
        NAME_AQUARIUS_URL: DEFAULT_NAME_AQUARIUS_URL,
    }
}


class Config(configparser.ConfigParser):

    def __init__(self, filename=None, **kwargs):
        """
        Initialize configuration file.

        Args:
            self: (todo): write your description
            filename: (str): write your description
        """
        configparser.ConfigParser.__init__(self)

        self.read_dict(config_defaults)
        self._section_name = ConfigSections.RESOURCES
        self._oceandb_name = ConfigSections.OCEANBD
        self._logger = kwargs.get('logger', logging.getLogger(__name__))
        self._logger.debug('Config: loading config file %s', filename)

        if filename:
            with open(filename) as fp:
                text = fp.read()
                self.read_string(text)
        else:
            if 'text' in kwargs:
                self.read_string(kwargs['text'])
        self._load_environ()

    def _load_environ(self):
        """
        Load all the configuration.

        Args:
            self: (todo): write your description
        """
        for option_name, environ_item in environ_names.items():
            value = os.environ.get(environ_item[0])
            if value is not None:
                self._logger.debug('Config: setting environ %s = %s', option_name, value)
                self.set(self._section_name, option_name, value)

    def set_arguments(self, items):
        """
        Set configuration options.

        Args:
            self: (todo): write your description
            items: (dict): write your description
        """
        for name, value in items.items():
            if value is not None:
                self._logger.debug('Config: setting argument %s = %s', name, value)

                self.set(self._section_name, name, value)

    @property
    def aquarius_url(self):
        """
        Returns the url of the replication url.

        Args:
            self: (dict): write your description
        """
        return self.get(self._section_name, NAME_AQUARIUS_URL)
    
    @property
    def allow_free_assets_only(self):
        """
        Returns a list of free assets.

        Args:
            self: (todo): write your description
        """
        return self.get(self._section_name, ALLOW_FREE_ASSETS_ONLY)

    @property
    def db_url(self):
        """
        Returns the url for the url.

        Args:
            self: (dict): write your description
        """
        return self.get(self._oceandb_name, DB_HOSTNAME) + ":" + self.get(self._oceandb_name,
                                                                          DB_PORT)

    @property
    def module(self):
        """
        The module that module.

        Args:
            self: (dict): write your description
        """
        return self.get(self._oceandb_name, MODULE)

    # static methods

    @staticmethod
    def get_environ_help():
        """
        Return the help string for the command.

        Args:
        """
        result = []
        for option_name, environ_item in environ_names.items():
            # codacy fix
            assert option_name
            result.append("{:20}{:40}".format(environ_item[0], environ_item[1]))
        return "\n".join(result)
