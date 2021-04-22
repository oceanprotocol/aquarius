#
# Copyright 2021 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import logging
import os
import time
from threading import Thread

import elasticsearch
from eth_utils import add_0x_prefix, remove_0x_prefix
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.ocean.util import from_base_18, to_base_18
from ocean_lib.web3_internal.event_filter import EventFilter
from web3.utils.events import get_event_data

from aquarius.app.dao import Dao
from aquarius.app.util import get_bool_env_value
from aquarius.block_utils import BlockProcessingClass
from aquarius.events.util import (
    get_datatoken_info,
    get_exchange_contract,
    prepare_contracts,
)

logger = logging.getLogger(__name__)


class MetadataUpdater(BlockProcessingClass):
    """Update price/liquidity info of all known assets.

    The update happens in two stages:
     1. Initial update is performed if this is ran for the first time. This is determined by
        checking for a cached block number from a previous run. The initial update extracts all
        Datatoken<>Ocean balancer pools by looking at the BFactory `BPoolRegistered` event. Then
        each Asset in the database is updated with the liquidity/price information from the
        corresponding pool.
     2. Periodic update is continuously running to detect liquidity updates by looking at the
        `LOG_JOIN`, `LOG_EXIT`, and `LOG_SWAP` event logs. The events are detected regardless of
        the pool contract, i.e. it looks at all matching events from all BPool contracts or
        even any smartcontract event that has the same signature.
        See `get_dt_addresses_from_pool_logs`

    Notes:
        - Set the `BFACTORY_BLOCK` envvar to tell the updater which `fromBlock` to start processing
          events. This should be set to the blockNumber in which the BFactory was created/deployed
        - The continuous updater runs every N seconds (initially set to 20s)
        - The price/liquidity info is added to the Asset's json object under the `price` key, e.g.:
                asset['price'] = {
                    'datatoken': 90,
                    'ocean': 10,
                    'value': 0.111,
                    'type': 'pool',
                    'address': '0x12112112112...',
                    'pools': ['0x12112112112...', ]
                }


    """

    DID_PREFIX = "did:op:"
    PRICE_TOO_LARGE = 1000000000

    def __init__(self, oceandb, other_db_index, web3, config):
        self._oceandb = oceandb
        self._other_db_index = other_db_index
        self._web3 = web3
        self._config = config

        self._addresses = prepare_contracts(self._web3, self._config)
        self._checksum_ocean = self._addresses.get("Ocean")
        if not self._checksum_ocean:
            self._checksum_ocean = os.getenv("OCEAN_ADDRESS")

        logger.debug(
            f"Ocean token address: {self._checksum_ocean}, \n"
            f"all deployed addresses: {self._addresses.items()}"
        )
        assert self._checksum_ocean, (
            f"Ocean token address is not found: addresses={self._addresses.keys()}.\n"
            f'Please add the "Ocean" token address in the address.json file or set the '
            f"`OCEAN_ADDRESS` environment variable."
        )
        self._OCEAN = self._checksum_ocean.lower()

        self.ex_contract = FixedRateExchange(get_exchange_contract(self._web3).address)
        assert (
            self.ex_contract and self.ex_contract.address
        ), "Failed to load FixedRateExchange contract."

        self._do_first_update = get_bool_env_value("METADATA_UPDATE_ALL", 1)
        self.bfactory_block = self.get_or_set_last_block()

        self._is_on = False
        default_quiet_time = 10
        try:
            self._quiet_time = os.getenv("OCN_METADATA_UPDATER_QUITE_TIME", 0)
        except ValueError:
            self._quiet_time = 0

        self._quiet_time = max(self._quiet_time, default_quiet_time)

    @property
    def is_running(self):
        return self._is_on

    @property
    def block_envvar(self):
        return "BFACTORY_BLOCK"

    def start(self):
        if self._is_on:
            return

        if not self._web3:
            logger.error("Cannot start MetadataUpdater without a web3 instance.")
            return

        if self._oceandb is None:
            logger.error("Cannot start MetadataUpdater  without an OceanDB instance.")
            return

        logger.info("Starting the MetadataUpdater.")
        t = Thread(target=self.run, daemon=True)
        self._is_on = True
        t.start()

    def is_first_update_enabled(self):
        return self._do_first_update

    def stop(self):
        self._is_on = False

    def run(self):
        if self._do_first_update:
            self.do_update()

        while True:
            try:
                if not self._is_on:
                    return

                self.process_pool_events()

            except (KeyError, Exception) as e:
                logger.error("Error doing update of Metadata.")
                logger.error(e)
                raise

            time.sleep(self._quiet_time)

    def _get_all_assets(self):
        for asset in self._oceandb.list():
            try:
                yield asset
            except (KeyError, Exception) as e:
                logging.error(str(e))

    def _get_event_signature(self, contract, event_name):
        e = getattr(contract.events, event_name)
        if not e:
            raise ValueError(
                f"Event {event_name} not found in {contract.CONTRACT_NAME} contract."
            )

        abi = e().abi
        types = [param["type"] for param in abi["inputs"]]
        sig_str = f'{event_name}({",".join(types)})'
        return self._web3.sha3(text=sig_str).hex()

    def get_last_processed_block(self):
        block = 0
        try:
            last_block_record = self._oceandb.driver.es.get(
                index=self._other_db_index, id="pool_events_last_block", doc_type="_doc"
            )["_source"]
            block = last_block_record["last_block"]
        except Exception as e:
            logger.error(f"Cannot get last_block error={e}")
        # no need to start from 0 if we have a deployment block
        bfactory_block = int(os.getenv("BFACTORY_BLOCK", 0))
        if block < bfactory_block:
            block = bfactory_block
        return block

    def store_last_processed_block(self, block):
        # make sure that we don't write a block < then needed
        stored_block = self.get_last_processed_block()
        if block <= stored_block:
            logger.error(
                f"Trying to write {block} as last_block, but we already have {stored_block}."
            )

        record = {"last_block": block}
        try:
            self._oceandb.driver.es.index(
                index=self._other_db_index,
                id="pool_events_last_block",
                body=record,
                doc_type="_doc",
                refresh="wait_for",
            )["_id"]

        except elasticsearch.exceptions.RequestError as e:
            logger.error(
                f"store_last_processed_block: block={block} type={type(block)}, error={e}"
            )

    def get_dt_addresses_from_exchange_logs(self, from_block, to_block=None):
        contract = FixedRateExchange(None)
        event_names = ["ExchangeCreated", "ExchangeRateChanged"]
        topic0_list = [self._get_event_signature(contract, en) for en in event_names]
        filters = []
        to_block = to_block or "latest"
        for i, event_name in enumerate(event_names):
            filters.append(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "topics": [topic0_list[i]],
                }
            )
        events = [getattr(contract.events, en) for en in event_names]
        event_abis = [e().abi for e in events]
        address_exid = []
        for i, _filter in enumerate(filters):
            try:
                logs = self._web3.eth.getLogs(_filter)
            except ValueError as e:
                logger.error(
                    f"get_dt_addresses_from_exchange_logs -> web3.eth.getLogs (filter={_filter}) failed: "
                    f"{e}.."
                )
                logs = []

            if logs:
                for log in logs:
                    log_topics = log["topics"]
                    parsed_log = get_event_data(event_abis[i], log)
                    if log_topics[0] == topic0_list[0]:
                        logger.debug(f"Processing ExchangeCreated: {parsed_log}")
                        address_exid.extend(
                            [
                                parsed_log.args.get("dataToken", ""),
                                add_0x_prefix(parsed_log.args.exchangeId.hex()),
                            ]
                        )
                    else:
                        # update event
                        logger.debug(f"Processing ExchangeRateChanged: {parsed_log}")
                        exchange_info = contract.getExchange(
                            parsed_log.args.exchangeId.hex()
                        )
                        address_exid.extend(
                            [
                                exchange_info.dataToken,
                                add_0x_prefix(parsed_log.args.exchangeId.hex()),
                            ]
                        )
                    # all_logs.append(parsed_log)
        return address_exid

    def get_dt_addresses_from_pool_logs(self, from_block, to_block=None):
        contract = BPool(None)
        event_names = ["LOG_JOIN", "LOG_EXIT", "LOG_SWAP"]
        topic0_list = [self._get_event_signature(contract, en) for en in event_names]
        args_list = [("tokenIn",), ("tokenOut",), ("tokenIn", "tokenOut")]
        filters = []
        to_block = to_block or "latest"
        for i, event_name in enumerate(event_names):
            filters.append(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "topics": [topic0_list[i]],
                }
            )

        events = [getattr(contract.events, en) for en in event_names]
        event_abis = [e().abi for e in events]
        # all_logs = []
        addresses = []
        for i, _filter in enumerate(filters):
            try:
                logs = self._web3.eth.getLogs(_filter)
            except ValueError as e:
                logger.error(
                    f"get_dt_addresses_from_pool_logs -> web3.eth.getLogs "
                    f"(filter={_filter}) failed: {e}.."
                )
                logs = []

            if logs:
                args = args_list[i]
                for log in logs:
                    parsed_log = get_event_data(event_abis[i], log)
                    addresses.extend(
                        [
                            (parsed_log.args.get(arg, ""), parsed_log.address)
                            for arg in args
                        ]
                    )
                    # all_logs.append(parsed_log)

        addresses_and_pools = [
            (a, pool) if a and a.lower() != self._OCEAN else ("", pool)
            for (a, pool) in addresses
        ]
        return addresses_and_pools

    def get_datatoken_pools(self, dt_address, from_block=0, to_block="latest"):
        contract = BPool(None)
        topic0 = self._get_event_signature(contract, "LOG_JOIN")
        topic2 = f"0x000000000000000000000000{remove_0x_prefix(dt_address).lower()}"
        filter_params = {
            "fromBlock": from_block,
            "toBlock": to_block,
            "topics": [topic0, None, topic2],
        }

        e = getattr(contract.events, "LOG_JOIN")
        event_abi = e().abi
        logs = self._web3.eth.getLogs(filter_params)
        if not logs:
            return None

        pools = {get_event_data(event_abi, log).address for log in logs}
        return list(pools)

    def _get_liquidity_and_price(self, pools, dt_address):
        assert pools, f"pools should not be empty, got {pools}"
        logger.debug(f" Searching {pools} for {dt_address}")
        dt_address_lower = dt_address.lower()
        pool_to_price = dict()
        for _pool in pools:
            try:
                pool = BPool(_pool)
                try:
                    ptokens = {a.lower() for a in pool.getCurrentTokens()}
                except Exception:
                    continue

                if self._OCEAN not in ptokens or dt_address_lower not in ptokens:
                    logger.debug(
                        f" ignore pool {_pool}, cannot find {self._OCEAN} and {dt_address_lower} in tokens list {ptokens}"
                    )
                    continue

                price = from_base_18(
                    pool.getSpotPrice(self._checksum_ocean, dt_address)
                )
                if price <= 0.0 or price > self.PRICE_TOO_LARGE:
                    continue

                pool_to_price[_pool] = price
                logger.debug(f" Adding pool {_pool} with price {price}")

            except Exception as e:
                logger.error(
                    f"failed to get liquidity/price info from pool {_pool} and datatoken {dt_address}: {e}"
                )

        if pool_to_price:
            _pool = sorted(pool_to_price.items(), key=lambda x: x[1])[0][0]
            dt_reserve, ocn_reserve, price, _pool = self.get_pool_reserves_and_price(
                _pool, dt_address
            )
            return dt_reserve, ocn_reserve, price, _pool

        # no pool or no pool with price was found
        return 0.0, 0.0, 0.0, pools[0]

    def get_pool_reserves_and_price(self, _pool, dt_address):
        pool = BPool(_pool)
        dt_reserve = pool.getBalance(dt_address)
        ocn_reserve = pool.getBalance(self._checksum_ocean)
        price_base = pool.calcInGivenOut(
            ocn_reserve,
            pool.getDenormalizedWeight(self._checksum_ocean),
            dt_reserve,
            pool.getDenormalizedWeight(dt_address),
            to_base_18(1.0),
            pool.getSwapFee(),
        )
        price = from_base_18(price_base)
        ocn_reserve = from_base_18(ocn_reserve)
        dt_reserve = from_base_18(dt_reserve)
        if dt_reserve <= 1.0:
            price = 0.0
        if price > self.PRICE_TOO_LARGE:
            price = 0.0

        return dt_reserve, ocn_reserve, price, _pool

    def _get_fixedrateexchange_price(self, dt_address, owner=None, exchange_id=None):
        fre = self.ex_contract
        try:
            if not exchange_id:
                assert (
                    owner is not None
                ), "owner is required when `exchange_id` is not given."
                exchange_id = add_0x_prefix(
                    fre.generateExchangeId(
                        self._checksum_ocean, dt_address, owner
                    ).hex()
                )

            ex_data = fre.getExchange(exchange_id)
            if not ex_data or not ex_data.exchangeOwner:
                return None, None, None

            price = from_base_18(ex_data.fixedRate)
            supply = from_base_18(ex_data.supply)
            return price, supply, exchange_id
        except Exception as e:
            logger.error(
                f"Reading exchange price failed for datatoken {dt_address}, "
                f"owner {owner}, exchangeId {exchange_id}: {e}"
            )
            return None, None, None

    def get_all_pools(self):
        bfactory = BFactory(self._addresses.get(BFactory.CONTRACT_NAME))
        event_name = "BPoolRegistered"
        event = getattr(bfactory.events, event_name)
        latest_block = self._web3.eth.blockNumber
        _from = self.bfactory_block
        chunk = self._blockchain_chunk_size
        pools = []
        while _from < latest_block:
            event_filter = EventFilter(
                event_name, event, None, from_block=_from, to_block=_from + chunk - 1
            )
            try:
                logs = event_filter.get_all_entries(max_tries=10)
                logs = sorted(logs, key=lambda l: l.blockNumber)
                pools.extend([log.args.bpoolAddress for log in logs])
            except ValueError as e:
                logger.error(
                    f"get_all_pools BFactory {bfactory.address}, fromBlock {_from}, toBlock{_from+chunk-1}: {e}"
                )
            _from += chunk

        return pools

    def _get_price_updates_from_fixed_rate_exchange(
        self, _dt_address, owner=None, exchange_id=None
    ):
        if exchange_id:
            price, dt_supply, exchange_id = self._get_fixedrateexchange_price(
                _dt_address, exchange_id=exchange_id
            )
        else:
            price, dt_supply, exchange_id = self._get_fixedrateexchange_price(
                _dt_address, owner
            )  # noqa

        logger.info(
            f"Updating price for asset with address {_dt_address}, with "
            f"owner={owner}"
            if owner
            else f"exchange_id={exchange_id}, " f"from FIXED RATE EXCHANGE."
        )

        is_consumable = str(bool(dt_supply is not None and dt_supply > 1)).lower()

        price_dict = {
            "datatoken": dt_supply or 0.0,
            "ocean": 0.0,
            "pools": [],
            "value": price or 0.0,
            "isConsumable": is_consumable,
        }

        logger.info(
            f"Setting datatoken={dt_supply or 0.0}, ocean=0.0, pools=[], "
            f"value={price or 0.0}. Found dt_supply={dt_supply}, setting "
            f"isConsumable={is_consumable}. "
        )

        if price is not None:
            logger.info(
                "Found price not None, setting "
                f"address={self.ex_contract.address}, type=exchange, and "
                "exchange_id as empty string."
            )
            price_dict.update(
                {"exchange_id": exchange_id, "type": "exchange", "address": ""}
            )
        else:
            logger.info(
                "Found price=None, setting address, type, and exchange_id as "
                "empty string."
            )  # noqa
            price_dict.update({"address": "", "type": "", "exchange_id": ""})
        return price_dict

    def _get_price_updates_from_liquidity(self, pools, _dt_address):
        dt_reserve, ocn_reserve, price, pool_address = self._get_liquidity_and_price(
            pools, _dt_address
        )

        is_consumable = str(bool(price is not None and price > 0.0)).lower()

        logger.info(
            f"Updating price for asset with address {_dt_address}, with"
            f" {len(pools)} pools found from LIQUIDITY AND PRICE."
            f"Setting datatoken={dt_reserve}, ocean={ocn_reserve}, "
            f"value={price}, type=pool, address={pool_address}"
            f"isConsumable={is_consumable}. "
        )

        return {
            "datatoken": dt_reserve,
            "ocean": ocn_reserve,
            "value": price,
            "type": "pool",
            "address": pool_address,
            "pools": pools,
            "isConsumable": is_consumable,
        }

    def do_single_update(self, asset):
        did_prefix = self.DID_PREFIX
        prefix_len = len(did_prefix)
        did = asset["id"]
        if not did.startswith(did_prefix):
            return

        dt_address = add_0x_prefix(did[prefix_len:])
        _dt_address = self._web3.toChecksumAddress(dt_address)
        pools = self.get_datatoken_pools(dt_address, from_block=self.bfactory_block)
        if pools:
            logger.info(
                f"Found pools for asset with address={_dt_address}, "
                f"Updating price from LIQUIDITY AND PRICE."
            )
            price_dict = self._get_price_updates_from_liquidity(pools, _dt_address)
        else:
            owner = asset["proof"].get("creator")
            if not owner or not self._web3.isAddress(owner):
                logger.warning(
                    f"updating price info for datatoken {dt_address} failed, invalid owner from ddo.proof (owner={owner})."
                )
                return

            logger.info(
                f"NO pools found for asset with address={_dt_address}. "
                f"Updating price from FIXED RATE EXCHANGE."
            )
            price_dict = self._get_price_updates_from_fixed_rate_exchange(
                dt_address, owner
            )

        asset["price"].update(price_dict)
        try:
            dt_info = get_datatoken_info(_dt_address)
        except Exception as e:
            logger.error(
                f"getting datatoken info failed for datatoken {_dt_address}: {e}"
            )
            dt_info = {}

        asset["dataTokenInfo"] = dt_info

        logger.info(
            f"doing single asset update: datatoken {dt_address}, pools {pools}, price-info {price_dict}"
        )
        self._oceandb.update(asset, did)

    def do_update(self):
        did_prefix = self.DID_PREFIX
        prefix_len = len(did_prefix)
        pools = self.get_all_pools()
        dt_to_pool = dict()
        for pool_address in pools:
            pool = BPool(pool_address)
            try:
                ptokens = pool.getCurrentTokens()
            except Exception:
                continue

            if len(ptokens) != 2 or ptokens[1].lower() != self._OCEAN:
                continue

            dt = add_0x_prefix(ptokens[0]).lower()
            if dt not in dt_to_pool:
                dt_to_pool[dt] = []

            dt_to_pool[dt].append(pool_address)

        for asset in self._get_all_assets():
            did = asset.get("id", None)
            if not did:
                logger.debug(f"db asset without id: {asset}")
                continue

            if not did.startswith(did_prefix):
                logger.warning(
                    f"skipping price info update for asset {did} because the did is invalid."
                )
                continue

            dt_address = add_0x_prefix(did[prefix_len:])
            _dt_address = self._web3.toChecksumAddress(dt_address)
            dt_address = dt_address.lower()
            pools = dt_to_pool.get(dt_address, [])

            if not pools:
                logger.info(
                    f"NO pools found for asset with address={_dt_address}. "
                    f"Updating price from FIXED RATE EXCHANGE."
                )
                owner = asset["proof"].get("creator")
                if not owner or not self._web3.isAddress(owner):
                    logger.warning(
                        f"updating price info for datatoken {dt_address} failed, invalid owner from ddo.proof (owner={owner})."
                    )
                    continue

                price_dict = self._get_price_updates_from_fixed_rate_exchange(
                    _dt_address, owner
                )
            else:
                logger.info(
                    f"Found pools for asset with address={_dt_address}, "
                    f"Updating price from LIQUIDITY AND PRICE."
                )

                price_dict = self._get_price_updates_from_liquidity(pools, _dt_address)

            asset["price"].update(price_dict)
            try:
                dt_info = get_datatoken_info(_dt_address)
            except Exception as e:
                logger.error(
                    f"getting datatoken info failed for datatoken {_dt_address}: {e}"
                )
                dt_info = {}

            asset["dataTokenInfo"] = dt_info

            logger.info(
                f"updating price info for datatoken: {dt_address}, pools {pools}, price-info {price_dict}"
            )
            self._oceandb.update(asset, did)

    def update_dt_assets_with_exchange_info(self, dt_address_exids):
        did_prefix = self.DID_PREFIX
        dao = Dao(oceandb=self._oceandb)
        seen_exs = set()
        for address, exid in zip(dt_address_exids[::2], dt_address_exids[1::2]):
            if not address or exid in seen_exs:
                continue
            seen_exs.add(exid)
            logger.debug(
                f"updating price info for datatoken: {address}, exchangeId {exid}"
            )
            did = did_prefix + remove_0x_prefix(address)
            try:
                asset = dao.get(did)
                _price_dict = asset.get("price", {})
                _pools = _price_dict.get("pools", [])
                if _price_dict.get("type") == "pool" and _pools:
                    # skip if the asset has pools
                    continue

                _dt_address = self._web3.toChecksumAddress(address)
                logger.info(
                    f"Found asset with exchange info address={_dt_address}, "
                    "Updating price from FIXED RATE EXCHANGE. "
                    "Not searching for pools."
                )
                price_dict = self._get_price_updates_from_fixed_rate_exchange(
                    _dt_address, exchange_id=exid
                )
                asset["price"].update(price_dict)
                asset["dataTokenInfo"] = get_datatoken_info(_dt_address)
                self._oceandb.update(asset, did)
                logger.info(
                    f"updated price info: dt={address}, exchangeAddress={self.ex_contract.address}, "
                    f'exchangeId={exid}, price={asset["price"]}'
                )
            except Exception as e:
                logger.error(
                    f"updating datatoken assets price values from exchange contract: {e}"
                )

    def update_dt_assets(self, dt_address_pool_list):
        did_prefix = self.DID_PREFIX
        dao = Dao(oceandb=self._oceandb)
        _dt_address_pool_list = []
        seen_pools = set()
        for address, pool_address in dt_address_pool_list:
            if pool_address in seen_pools:
                continue

            seen_pools.add(pool_address)
            if not address:
                address = BPool(pool_address).getCurrentTokens()[0]

            _dt_address_pool_list.append((address, pool_address))

        dt_to_pools = {a: [] for a, p in _dt_address_pool_list}
        for address, pool_address in _dt_address_pool_list:
            dt_to_pools[address].append(pool_address)

        asset = None
        for address, pools in dt_to_pools.items():

            did = did_prefix + remove_0x_prefix(address)
            try:
                asset = dao.get(did)
            except Exception as e:
                logger.debug(f"asset not found for token address {address}: {e}")
                continue

            logger.info(f"updating price info for datatoken: {address}, pools {pools}")
            try:

                _price_dict = asset.get("price", {})
                _pools = _price_dict.get("pools", [])
                _dt_address = self._web3.toChecksumAddress(address)
                _pools.extend([p for p in pools if p not in _pools])
                logger.debug(f"Pools to be checked: {_pools}")

                logger.info(
                    f"Found asset with exchange info address={_dt_address}, "
                    "Updating price from LIQUIDITY AND PRICE. "
                    f"Pools are assumed to exist ({len(_pools)}) found)."
                )
                price_dict = self._get_price_updates_from_liquidity(_pools, _dt_address)
                asset["price"].update(price_dict)
                asset["dataTokenInfo"] = get_datatoken_info(_dt_address)

                self._oceandb.update(asset, did)
                logger.info(
                    f'updated price info: dt={address}, pool={pool_address}, price={asset["price"]}'
                )
            except Exception as e:
                logger.error(f"updating datatoken assets price/liquidity values: {e}")

    def process_pool_events(self):
        last_block = self.get_last_processed_block()
        current_block = self._web3.eth.blockNumber
        if (
            not current_block
            or not isinstance(current_block, int)
            or current_block <= last_block
        ):
            return

        from_block = last_block

        start_block_chunk = from_block
        for end_block_chunk in range(
            from_block, current_block, self._blockchain_chunk_size
        ):
            self.process_block_range(start_block_chunk, end_block_chunk)
            start_block_chunk = end_block_chunk
        # Process last few blocks because range(start, end) doesn't include end
        self.process_block_range(start_block_chunk, end_block_chunk)

    def process_block_range(self, from_block, to_block):
        logger.debug(
            f"Price/Liquidity monitor >>>> from_block:{from_block}, current_block:{to_block} <<<<"
        )
        if from_block > to_block:
            return

        ok = False
        try:
            dt_address_pool_list = self.get_dt_addresses_from_pool_logs(
                from_block=from_block, to_block=to_block
            )
            logger.debug(f"Got pools: {dt_address_pool_list}")
            self.update_dt_assets(dt_address_pool_list)
            dt_address_exchange = self.get_dt_addresses_from_exchange_logs(
                from_block=from_block, to_block=to_block
            )
            logger.debug(f"Got dt/exchanges: {dt_address_exchange}")
            self.update_dt_assets_with_exchange_info(dt_address_exchange)
            ok = True

        except Exception as e:
            logging.error(f"process_pool_events: {e}")

        finally:
            if ok and isinstance(to_block, int):
                self.store_last_processed_block(to_block)
