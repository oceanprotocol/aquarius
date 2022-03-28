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
    "Flask==2.0.3",
    "Flask-Cors==3.0.10",
    "flask-swagger==0.2.14",
    "flask-swagger-ui==3.36.0",
    "Jinja2>=2.10.1",
    "requests>=2.21.0",
    "gunicorn==20.1.0",
    "elasticsearch==8.1.1",
    "PyYAML==6.0",
    "pytz==2021.3",
    "ocean-contracts==1.0.0a26",
    "web3==5.28.0",
    "gevent",
    "json-sempai==0.4.0",
    "python-dateutil==2.8.2",
    "pyshacl==0.19.0",
    "gql==3.1.0",
    "aiohttp==3.8.1",
]

setup_requirements = ["pytest-runner==6.0.0"]

dev_requirements = [
    "bumpversion==0.6.0",
    "pkginfo==1.8.2",
    "twine==3.8.0",
    "flake8",
    "isort",
    "black",
    "pre-commit",
    # not virtualenv: devs should already have it before pip-installing
    "watchdog==2.1.6",
    "licenseheaders",
]

test_requirements = [
    "Flask==2.0.3",
    "codacy-coverage==1.3.11",
    "coverage==6.3.2",
    "mccabe==0.6.1",
    "pylint==2.12.2",
    "pytest",
    "pytest-env",
    "freezegun==1.2.1",
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
    version='4.0.2',
    # fmt: on
    zip_safe=False,
)
