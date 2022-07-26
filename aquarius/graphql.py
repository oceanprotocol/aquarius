#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.aiohttp import log as aiohttp_logger

from aquarius.events.util import get_network_name

logger = logging.getLogger("aquarius")
aiohttp_logger.setLevel(logging.WARNING)


def get_number_orders_price(token_address, last_sync_block, chain_id):
    try:
        client = get_client(chain_id)

        last_block = get_last_block(client)
        while last_block < last_sync_block:
            logger.debug(
                f"Waiting for sync with subgraph, currently at last block {last_block}."
            )
            last_block = get_last_block(client)
            time.sleep(2)

        query = gql(
            '{tokens(where:{nft:"'
            + token_address.lower()
            + '"}){orderCount, fixedRateExchanges{ price }, dispensers{id}}}'
        )
        tokens_result = client.execute(query)
        logger.debug(f"Got result for did query: {tokens_result}.")

        order_count = tokens_result["tokens"][0]["orderCount"]
        price = -1
        fres = tokens_result["tokens"][0].get("fixedRateExchanges", None)
        dispensers = tokens_result["tokens"][0].get("dispensers", None)
        if fres:
            price = fres[0].get("price", -1)
        elif dispensers:
            price = 0

        return int(order_count), float(price)
    except Exception:
        logger.exception(
            f"Can not get number of orders for subgraph {get_network_name()} token address {token_address}"
        )
        return -1, -1


def get_transport(chain_id):
    subgraph_urls = json.loads(os.getenv("SUBGRAPH_URLS", "{}"))

    if str(chain_id) not in subgraph_urls:
        raise Exception("Subgraph not defined for this chain.")

    prefix = subgraph_urls[str(chain_id)]

    url = f"{prefix}/subgraphs/name/oceanprotocol/ocean-subgraph"
    logger.debug(f"Creating transport for {url}.")

    return AIOHTTPTransport(url=url)


def get_client(chain_id):
    logger.debug("Initializing client for transport and fetching schema.")
    return Client(transport=get_transport(chain_id), fetch_schema_from_transport=True)


def get_last_block(client):
    last_block_query = gql("{_meta { block { number } } }")

    try:
        result = client.execute(last_block_query)
        last_block = result["_meta"]["block"]["number"]
    except (KeyError, IndexError):
        raise IndexError(
            "Can not get last block name for subgraph {get_network_name()}"
        )

    return last_block
