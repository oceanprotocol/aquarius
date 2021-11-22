#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

from enum import Enum, IntEnum


class Events(Enum):
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


class AquariusCustomDDOFields(Enum):
    EVENT = "event"
    NFT = "nft"
    DATATOKENS = "datatokens"
    STATS = "stats"
