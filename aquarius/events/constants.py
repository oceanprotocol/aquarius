#
# Copyright 2023 Ocean Protocol Foundation
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
    hashes = {
        "0x5463569dcc320958360074a9ab27e809e8a6942c394fb151d139b5f7b4ecb1bd": {
            "type": EVENT_METADATA_CREATED,
            "text": "MetadataCreated(address,uint8,string,bytes,bytes,bytes32,uint256,uint256)",
        },
        "0xe5c4cf86b1815151e6f453e1e133d4454ae3b0b07145db39f2e0178685deac84": {
            "type": EVENT_METADATA_UPDATED,
            "text": "MetadataUpdated(address,uint8,string,bytes,bytes,bytes32,uint256,uint256)",
        },
        "0xa8336411cc72db0e5bdc4dff989eeb35879bafaceffb59b54b37645c3395adb9": {
            "type": EVENT_METADATA_STATE,
            "text": "MetadataState(address,uint8,uint256,uint256)",
        },
        "0xe1c4fa794edfa8f619b8257a077398950357b9c6398528f94480307352f9afcc": {
            "type": EVENT_ORDER_STARTED,
            "text": "OrderStarted(address,address,uint256,uint256,uint256,address,uint256)",
        },
        "0x6de6cd3982065cbd31e789e3109106f4d76d1c8a46e85262045cf947fb3fd4ed": {
            "type": EVENT_TOKEN_URI_UPDATE,
            "text": "TokenURIUpdate(address,string,uint256,uint256,uint256)",
        },
        "0xeb7a353641f7d3cc54b497ef1553fdc292b64d9cc3be8587c23dfba01f310b19": {
            "type": EVENT_EXCHANGE_CREATED,
            "text": "ExchangeCreated(bytes32,address,address,address,uint256)",
        },
        "0xe50f9919fdc524004a4ee0cb934f4734f144bec0713a52e5483b753f5de0f08c": {
            "type": EVENT_EXCHANGE_RATE_CHANGED,
            "text": "ExchangeRateChanged(bytes32,address,uint256)",
        },
        "0x7d0aa581e6eb87e15f58588ff20c39ff6622fc796ec9bb664df6ed3eb02442c9": {
            "type": EVENT_DISPENSER_CREATED,
            "text": "DispenserCreated(address,address,uint256,uint256,address)",
        },
    }


class MetadataStates(IntEnum):
    ACTIVE = 0
    END_OF_LIFE = 1
    DEPRECATED = 2
    REVOKED = 3
    ORDERING_DISABLED = 4


SoftDeleteMetadataStates = [
    MetadataStates.DEPRECATED,
    MetadataStates.REVOKED,
]


class AquariusCustomDDOFields(SimpleEnum):
    EVENT = "event"
    NFT = "nft"
    DATATOKENS = "datatokens"
    STATS = "stats"
