#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

"""The setup script."""
#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.md") as history_file:
    history = history_file.read()

install_requirements = [
    "coloredlogs==15.0.1",
    "Flask==2.0.1",
    "Flask-Cors==3.0.10",
    "flask-swagger==0.2.14",
    "flask-swagger-ui==3.36.0",
    "Jinja2>=2.10.1",
    "requests>=2.21.0",
    "gunicorn==20.1.0",
    "PyYAML==5.4.1",
    "pytz==2021.1",
    "ocean-contracts==0.6.4",
    "web3==5.19.0",
    "jsonschema==3.2.0",
    "eciespy",
    "gevent",
    "json-sempai==0.4.0",
    "python-dateutil==2.8.1",
]

setup_requirements = ["pytest-runner==5.3.1"]

dev_requirements = [
    "bumpversion==0.6.0",
    "pkginfo==1.7.1",
    "twine==3.4.1",
    "flake8",
    "isort",
    "black",
    "pre-commit",
    # not virtualenv: devs should already have it before pip-installing
    "watchdog==2.1.3",
    "licenseheaders",
]

test_requirements = [
    "Flask==2.0.1",
    "codacy-coverage==1.3.11",
    "coverage==5.5",
    "mccabe==0.6.1",
    "pylint==2.9.3",
    "pytest",
    "tox",
    "pytest-env",
    "freezegun==1.1.0",
]

setup(
    author="leucothia",
    author_email="devops@oceanprotocol.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="🐳 Ocean aquarius.",
    extras_require={
        "test": test_requirements,
        "dev": dev_requirements + test_requirements,
    },
    include_package_data=True,
    install_requires=install_requirements,
    keywords="ocean-aquarius",
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="ocean-aquarius",
    packages=find_packages(include=["aquarius", "aquarius.app"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/oceanprotocol/aquarius",
    # fmt: off
    # bumpversion needs single quotes
    version='2.2.12',
    # fmt: on
    zip_safe=False,
)
