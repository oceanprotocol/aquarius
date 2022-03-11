#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os
from typing import Optional

from flask_caching import Cache
from aquarius.myapp import app

logger = logging.getLogger(__name__)

cache = Cache(
    app,
    config={
        "CACHE_TYPE": "redis",
        "CACHE_KEY_PREFIX": "ocean_aquarius",
        "CACHE_REDIS_URL": os.getenv("REDIS_CONNECTION"),
    },
)


def get_cached_block():
    """
    Retrieves the latest block value.
    :return: `cached_block` stored in the database
    """
    return cache.get("cached_block")


def update_cached_block(cached_block: Optional[int]):
    """
    Updates the value of `cached_block` in the database
    :param: cached_block
    """
    if cached_block is None:
        msg = "Cached block is None."
        logger.error(msg)
        raise Exception(msg)

    block = get_or_create_cached_block(cached_block)
    cache.set("cached_block", block)
    assert cache.get("cached_block") == block, "The block was not updated."
    logger.info("Successfully updated the cached block")


def get_or_create_cached_block(cached_block: int):
    cache.set("cached_block", cached_block)
    return cached_block
