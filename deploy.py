#!/usr/bin/env python
import json
import os

from web3 import Web3

from aquarius.events.util import deploy_contract


def main():
    rpc = 'http://127.0.0.1:8545'
    web3 = Web3(Web3.HTTPProvider(os.getenv('EVENTS_RPC', rpc)))
    private_key = os.getenv('EVENTS_TESTS_PRIVATE_KEY')
    artifacts_path = os.getenv('ARTIFACTS_PATH', './aquarius/artifacts')
    address_file = os.path.join(artifacts_path, 'address.json')

    address_map = {'ganache': {}}

    ddo_file_path = os.path.join(artifacts_path, 'Metadata.json')
    address_map['ganache']['Metadata'] = deploy_contract(web3, json.load(open(ddo_file_path)), private_key)

    with open(address_file, 'w') as f:
        json.dump(address_map, f, indent=2)

    print(address_map['ganache']['Metadata'])


def setenv(key, value):
    # os.putenv(key, value) #Do *not* use putenv(), it doesn't work
    os.environ[key] = value


if __name__ == '__main__':
    main()
