#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os

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
    :return: `cached_block` stored in the database
    """
    result = cache.get("cached_block")
    logger.info(f"result:{result}")
    return result if result else None


def update_cached_block(cached_block):
    """
    Updates the value of `cached_block` in the database
    :param: cached_block
    """
    if cached_block is None:
        logger.error("Cached block is None.")
        return

    block = get_or_create_cached_block(cached_block)
    logger.info(f"block:{block}")
    cache.set("cached_block", block)
    logger.info(f'cache={cache.get("cached_block")}')


def get_or_create_cached_block(cached_block):
    cache.set("cached_block", cached_block)
    return cached_block
