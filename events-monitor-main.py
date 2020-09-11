import logging
import os
import time

from aquarius.app.util import get_contract_address_and_abi_file
from aquarius.events.events_monitor import EventsMonitor
from aquarius.log import setup_logging


logger = logging.getLogger(__name__)


def run_events_monitor():
    setup_logging()
    logger.info('EventsMonitor: preparing')
    required_env_vars = [
        'ARTIFACTS_PATH',
        'EVENTS_RPC',
        'CONFIG_FILE'
    ]
    for envvar in required_env_vars:
        if not os.getenv(envvar):
            raise AssertionError(
                f'env var {envvar} is missing, make sure to set the following '
                f'environment variables before starting the events monitor: {required_env_vars}')

    network_rpc = os.environ.get('EVENTS_RPC', 'http:127.0.0.1:8545')
    contract_address, contract_abi_file = get_contract_address_and_abi_file()

    config_file = os.getenv('CONFIG_FILE', 'config.ini')
    logger.info(f'EventsMonitor: starting with the following values: rpc={network_rpc}, contract={contract_address}')
    monitor = EventsMonitor(network_rpc, contract_address, contract_abi_file, config_file)
    monitor.start_events_monitor()
    logger.info(f'EventsMonitor: started')
    while True:
        time.sleep(5)


if __name__ == '__main__':
    run_events_monitor()