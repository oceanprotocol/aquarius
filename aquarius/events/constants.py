#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

from enum import IntEnum


class SimpleEnum:
    """This class can be used as a replacement for enum.Enum class.
    - The attributes are accessible with `ClassName.ATTR`
    - :func:`get_value` returns the value for a given key
    - :func:`get_all_keys` returns a list of all the keys
    - :func:`get_all_values` returns a list of all the values
    """

    @classmethod
    def get_value(cls, key):
        return getattr(cls, key)

    @classmethod
    def get_all_keys(cls):
        return [
            key
            for key in cls.__dict__.keys()
            if not key.startswith("_") and not callable(cls.get_value(key))
        ]

    @classmethod
    def get_all_values(cls):
        return [cls.get_value(key) for key in cls.get_all_keys()]


class EventTypes(SimpleEnum):
    EVENT_METADATA_CREATED = "MetadataCreated"
    EVENT_METADATA_UPDATED = "MetadataUpdated"
    EVENT_METADATA_STATE = "MetadataState"
    EVENT_ORDER_STARTED = "OrderStarted"
    EVENT_TOKEN_URI_UPDATE = "TokenURIUpdate"
    EVENT_EXCHANGE_CREATED = "ExchangeCreated"
    EVENT_EXCHANGE_RATE_CHANGED = "ExchangeRateChanged"
    EVENT_DISPENSER_CREATED = "DispenserCreated"
    EVENT_TRANSFER = "Transfer"


class MetadataStates(IntEnum):
    ACTIVE = 0
    END_OF_LIFE = 1
    DEPRECATED = 2
    REVOKED = 3
    ORDERING_DISABLED = 4


class AquariusCustomDDOFields(SimpleEnum):
    EVENT = "event"
    NFT = "nft"
    DATATOKENS = "datatokens"
    STATS = "stats"
