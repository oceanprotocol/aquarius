#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import json
import logging
import os
import time
from eth_utils.address import to_checksum_address

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.aiohttp import log as aiohttp_logger

from aquarius.events.util import get_network_name

logger = logging.getLogger("aquarius")
aiohttp_logger.setLevel(logging.WARNING)


class Price:
    def __init__(self, value):
        self.value = float(value)
        self.token_address = None
        self.token_symbol = None

    def as_dict(self):
        result = {"value": self.value}

        if self.token_address:
            result["tokenAddress"] = self.token_address

        if self.token_symbol:
            result["tokenSymbol"] = self.token_symbol

        return result


def get_number_orders_price(token_address, last_sync_block, chain_id):
    try:
        client = get_client(chain_id, last_sync_block)
        if not client:
            return -1, {}
        query = gql(
            '{tokens(where:{nft:"'
            + token_address.lower()
            + '"}){orderCount, fixedRateExchanges{ price, baseToken {symbol, address} }, dispensers{id}}}'
        )
        tokens_result = client.execute(query)
        logger.debug(f"Got result for did query: {tokens_result}.")

        order_count = tokens_result["tokens"][0]["orderCount"]
        price = None
        fres = tokens_result["tokens"][0].get("fixedRateExchanges", None)
        dispensers = tokens_result["tokens"][0].get("dispensers", None)
        if fres and "price" in fres[0]:
            price = Price(fres[0]["price"])
            if "baseToken" in fres[0]:
                price.token_address = to_checksum_address(
                    fres[0]["baseToken"].get("address")
                )
                price.token_symbol = fres[0]["baseToken"].get("symbol")
        elif dispensers:
            price = Price(0)

        price_obj = price.as_dict() if price else {}

        return int(order_count), price_obj
    except Exception:
        logger.exception(
            f"Can not get number of orders for subgraph {get_network_name()} token address {token_address}"
        )
        return -1, {}


def get_nft_transfers(start_block, last_sync_block, chain_id):
    try:
        client = get_client(chain_id, last_sync_block)
        if not client:
            return None
        query_text = (
            "{nftTransferHistories(where:{block_gt: "
            + str(start_block)
            + ","
            + " block_lte: "
            + str(last_sync_block)
            + " } orderBy: block orderDirection:asc skip:0 first:1000)"
            + "{nft{id},newOwner{id},block}}"
        )
        query = gql(query_text)
        transfers_result = client.execute(query)
        return transfers_result["nftTransferHistories"]
    except Exception:
        logger.exception(
            f"Can not get nft transfers from subgraph {get_network_name()}"
        )
        return None


def get_transport(chain_id):
    subgraph_urls = json.loads(os.getenv("SUBGRAPH_URLS", "{}"))

    if str(chain_id) not in subgraph_urls:
        logger.warn(f"Subgraph not defined for chain {chain_id}.")
        raise Exception("Subgraph not defined for this chain.")

    prefix = subgraph_urls[str(chain_id)]

    url = f"{prefix}/subgraphs/name/oceanprotocol/ocean-subgraph"
    logger.debug(f"Creating transport for {url}.")

    return AIOHTTPTransport(url=url)


def get_last_block(client):
    """Get current block height from subgraph
    Args:
        client:
    """
    last_block_query = gql("{_meta { block { number } } }")

    try:
        result = client.execute(last_block_query)
        last_block = result["_meta"]["block"]["number"]
    except (KeyError, IndexError):
        raise IndexError(
            "Can not get last block name for subgraph {get_network_name()}"
        )

    return last_block


def get_client(chain_id, block=None):
    """Gets a graphql client, and optionally, wait until subgraph syncs at least to a certain block

    Args:
        block: minimum block height
    """
    logger.debug("Initializing client for transport and fetching schema.")
    try:
        client = Client(
            transport=get_transport(chain_id), fetch_schema_from_transport=True
        )
    except Exception as e:
        logger.warning(f"Failed to initialize graphql client: {e}")
        return None
    if block is None:
        return client
    # wait for subgraph to sync
    last_block = get_last_block(client)
    while last_block < block:
        logger.debug(
            f"Waiting for sync with subgraph, currently at last block {last_block}."
        )
        last_block = get_last_block(client)
        time.sleep(2)

    return client
