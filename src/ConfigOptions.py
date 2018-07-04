import os
import json

from singletonify import singleton

from util import get_config_file


@singleton
class ConfigOptions(object):
    def __init__(self, config_file=None):
        if not config_file:
            config_file = get_config_file()

        self.config_dict = dict()
        if config_file and os.path.isfile(config_file):
            with open(config_file, 'r') as infile:
                config_dict = json.load(infile)
                self.config_dict = config_dict

    def getValue(self, key):
        return self.config_dict.get(key, None)
