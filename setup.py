#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

install_requirements = [
    'coloredlogs==14.0',
    'Flask==1.1.2',
    'Flask-Cors==3.0.8',
    'flask-swagger==0.2.14',
    'flask-swagger-ui==3.25.0',
    'Jinja2>=2.10.1',
    'requests>=2.21.0',
    'gunicorn==20.0.4',
    'oceandb-driver-interface==0.2.0',
    'oceandb-mongodb-driver==0.2.2',
    'oceandb-elasticsearch-driver==0.3.3',
    'PyYAML==5.3.1',
    'pytz==2020.1',
    'plecos==1.1.0',
    'web3==5.11.1',
    'eth-account==0.5.2',
    'eciespy'
]

setup_requirements = ['pytest-runner==5.2', ]

dev_requirements = [
    'bumpversion==0.6.0',
    'pkginfo==1.5.0.1',
    'twine==3.1.1',
    # not virtualenv: devs should already have it before pip-installing
    'watchdog==0.10.2',
]

test_requirements = [
    'plecos==1.0.2',
    'Flask==1.1.2',
    'web3==5.11.1',
    'codacy-coverage==1.3.11',
    'coverage==5.1',
    'mccabe==0.6.1',
    'pylint==2.5.3',
    'pytest',
    'tox',
]

setup(
    author="leucothia",
    author_email='devops@oceanprotocol.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="🐳 Ocean aquarius.",
    extras_require={
        'test': test_requirements,
        'dev': dev_requirements + test_requirements,
    },
    include_package_data=True,
    install_requires=install_requirements,
    keywords='ocean-aquarius',
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name='ocean-aquarius',
    packages=find_packages(include=['aquarius', 'aquarius.app']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/oceanprotocol/aquarius',
    version='2.0.0',
    zip_safe=False,
)
