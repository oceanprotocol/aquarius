#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

from enum import IntEnum

"""
Defines values of variables:
1. `EVENT_METADATA_CREATED`
2. `EVENT_METADATA_UPDATED`.
3. `EVENT_METADATA_STATE`.
4. `EVENT_ORDER_STARTED`
"""
EVENT_METADATA_CREATED = "MetadataCreated"
EVENT_METADATA_UPDATED = "MetadataUpdated"
EVENT_METADATA_STATE = "MetadataState"
EVENT_ORDER_STARTED = "OrderStarted"


class MetadataStates(IntEnum):
    ACTIVE = 0
    END_OF_LIFE = 1
    DEPRECATED = 2
    REVOKED = 3
    ORDERING_DISABLED = 4
