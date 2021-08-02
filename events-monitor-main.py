#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os
import time
import http.server
import socketserver

from aquarius.events.events_monitor import EventsMonitor
from aquarius.events.util import setup_web3
from aquarius.log import setup_logging

logger = logging.getLogger(__name__)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Construct a server response.
        self.send_response(200)
        self.end_headers()
        return


def run_events_monitor():
    setup_logging()
    logger.info("EventsMonitor: preparing")
    required_env_vars = ["EVENTS_RPC", "AQUARIUS_CONFIG_FILE"]
    for envvar in required_env_vars:
        if not os.getenv(envvar):
            raise AssertionError(
                f"env var {envvar} is missing, make sure to set the following "
                f"environment variables before starting the events monitor: {required_env_vars}"
            )

    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    monitor = EventsMonitor(setup_web3(config_file, logger), config_file)
    monitor.start_events_monitor()

    logger.info("EventsMonitor: started")
    if os.getenv("EVENTS_HTTP", None):
        logger.info("Events HTTP probing started on port 5001..")
        httpd = socketserver.TCPServer(("", 5001), Handler)
        httpd.serve_forever()
    else:
        while True:
            time.sleep(5)


if __name__ == "__main__":
    run_events_monitor()
