#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os
from aquarius.retry_mechanism import RetryMechanism


def test_add_get(client, base_ddo_url, events_object, monkeypatch):
    config_file = os.getenv("AQUARIUS_CONFIG_FILE", "config.ini")
    mechanism = RetryMechanism(
        config_file,
        events_object._es_instance,
        events_object._retries_db_index,
        None
    )

    mechanism.add_to_retry_queue()
    mechanism.get_from_retry_queue()
