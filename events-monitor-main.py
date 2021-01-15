import logging
import os
import time

from ocean_lib.config import Config
from ocean_lib.config_provider import ConfigProvider
from ocean_lib.web3_internal.contract_handler import ContractHandler
from ocean_lib.web3_internal.web3_provider import Web3Provider

from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.util import get_artifacts_path, get_network_name
from aquarius.log import setup_logging

logger = logging.getLogger(__name__)


def run_events_monitor():
    setup_logging()
    logger.info("EventsMonitor: preparing")
    required_env_vars = ["EVENTS_RPC", "CONFIG_FILE"]
    for envvar in required_env_vars:
        if not os.getenv(envvar):
            raise AssertionError(
                f"env var {envvar} is missing, make sure to set the following "
                f"environment variables before starting the events monitor: {required_env_vars}"
            )

    network_rpc = os.environ.get("EVENTS_RPC", "http:127.0.0.1:8545")

    config_file = os.getenv("CONFIG_FILE", "config.ini")
    logger.info(f"EventsMonitor: starting with the following values: rpc={network_rpc}")

    ConfigProvider.set_config(Config(config_file))
    from ocean_lib.ocean.util import get_web3_connection_provider

    Web3Provider.init_web3(provider=get_web3_connection_provider(network_rpc))
    ContractHandler.set_artifacts_path(get_artifacts_path())
    if get_network_name().lower() == "rinkeby":
        from web3.middleware import geth_poa_middleware

        Web3Provider.get_web3().middleware_stack.inject(geth_poa_middleware, layer=0)

    monitor = EventsMonitor(Web3Provider.get_web3(), config_file)
    monitor.start_events_monitor()
    logger.info("EventsMonitor: started")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    run_events_monitor()
