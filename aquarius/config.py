#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import configparser


def get_version():
    conf = configparser.ConfigParser()
    conf.read(".bumpversion.cfg")
    return conf["bumpversion"]["current_version"]
