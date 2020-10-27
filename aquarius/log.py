#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

import logging
import logging.config
import os

import coloredlogs
import yaml


def setup_logging(default_path='logging.yaml', default_level=None, env_key='LOG_CFG'):
    """Logging Setup"""
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value

    log_level_name = os.getenv('LOG_LEVEL', None)

    if not default_level:
        level_map = {
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        default_level = logging.INFO
        if log_level_name:
            default_level = level_map.get(log_level_name, logging.INFO)

    print(f'default log level: {default_level}, env var LOG_LEVEL {os.getenv("LOG_LEVEL", "NOT SET")}')

    if os.path.exists(path):
        with open(path, 'rt') as f:
            try:
                config = yaml.safe_load(f.read())
                if log_level_name:
                    for logger in config['loggers']:
                        if logger == 'elasticsearch':
                            continue

                        config['loggers'][logger]['level'] = log_level_name
                logging.config.dictConfig(config)
                coloredlogs.install()
            except Exception as e:
                print(f'Error in Logging Configuration (using default configs): {e}')
                logging.basicConfig(level=default_level)
                coloredlogs.install(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        coloredlogs.install(level=default_level)
        print('Failed to load configuration file. Using default configs')
