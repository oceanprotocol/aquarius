import logging
import os
import time

from aquarius.events.util import start_events_monitor
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

    config_file = os.getenv("CONFIG_FILE", "config.ini")
    start_events_monitor(config_file, logger)
    logger.info("EventsMonitor: started")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    run_events_monitor()
