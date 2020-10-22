import logging
import os
import time
from threading import Thread

import elasticsearch
from eth_utils import add_0x_prefix
from eth_utils import remove_0x_prefix
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.ocean.util import from_base_18, to_base_18
from ocean_lib.web3_internal.event_filter import EventFilter
from web3.utils.events import get_event_data

from aquarius.app.dao import Dao
from aquarius.events.util import prepare_contracts, get_datatoken_info, get_exchange_contract

logger = logging.getLogger(__name__)


class MetadataUpdater:
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

    def __init__(self, oceandb, web3, config):
        self._oceandb = oceandb
        self._web3 = web3
        self._config = config

        self._addresses = prepare_contracts(self._web3, self._config)
        self._checksum_ocean = self._addresses.get('Ocean')
        if not self._checksum_ocean:
            self._checksum_ocean = os.getenv('OCEAN_ADDRESS')

        logger.debug(f'Ocean token address: {self._checksum_ocean}, \n'
                     f'all deployed addresses: {self._addresses.items()}')
        assert self._checksum_ocean, \
            f'Ocean token address is not found: addresses={self._addresses.keys()}.\n' \
            f'Please add the "Ocean" token address in the address.json file or set the ' \
            f'`OCEAN_ADDRESS` environment variable.'
        self._OCEAN = self._checksum_ocean.lower()

        self.ex_contract = get_exchange_contract(self._web3)
        assert self.ex_contract and self.ex_contract.address, 'Failed to load FixedRateExchange contract.'

        self.bfactory_block = int(os.getenv('BFACTORY_BLOCK', 0))
        self._do_first_update = bool(int(os.getenv('METADATA_UPDATE_ALL', 1)) == 1)
        try:
            self.get_last_processed_block()
            # self._do_first_update = False
        except Exception:
            self.store_last_processed_block(self.bfactory_block)

        self._is_on = False
        default_quiet_time = 10
        try:
            self._quiet_time = os.getenv('OCN_METADATA_UPDATER_QUITE_TIME', 0)
        except ValueError:
            self._quiet_time = 0

        self._quiet_time = max(self._quiet_time, default_quiet_time)

    @property
    def is_running(self):
        return self._is_on

    def start(self):
        if self._is_on:
            return

        if not self._web3:
            logger.error(
                'Cannot start MetadataUpdater without a web3 instance.')
            return

        if self._oceandb is None:
            logger.error(
                'Cannot start MetadataUpdater  without an OceanDB instance.')
            return

        logger.info(f'Starting the MetadataUpdater.')
        t = Thread(
            target=self.run,
            daemon=True,
        )
        self._is_on = True
        t.start()

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
                logger.error(f'Error doing update of Metadata.')
                logger.error(e)
                raise

            time.sleep(self._quiet_time)

    def _get_all_assets(self):
        for asset in self._oceandb.list():
            try:
                yield self._oceandb.read(asset['id'])
            except (KeyError, Exception) as e:
                logging.error(str(e))

    def _get_event_signature(self, contract, event_name):
        e = getattr(contract.events, event_name)
        if not e:
            raise ValueError(f'Event {event_name} not found in {contract.CONTRACT_NAME} contract.')

        abi = e().abi
        types = [param['type'] for param in abi['inputs']]
        sig_str = f'{event_name}({",".join(types)})'
        return self._web3.sha3(text=sig_str).hex()

    def get_last_processed_block(self):
        last_block_record = self._oceandb.read('pool_events_last_block')
        last_block = last_block_record['last_block']
        return last_block

    def store_last_processed_block(self, block):
        record = {"last_block": block}
        try:
            self._oceandb.update(record, 'pool_events_last_block')
        except elasticsearch.exceptions.RequestError as e:
            logger.error(f'store_last_processed_block: block={block} type={type(block)}, error={e}')

    def get_dt_addresses_from_exchange_logs(self, from_block, to_block=None):
        contract = FixedRateExchange(None)
        event_names = ['ExchangeCreated']  # , 'ExchangeRateChanged']
        topic0_list = [self._get_event_signature(contract, en) for en in event_names]
        args_list = [('dataToken',)]
        filters = []
        to_block = to_block or 'latest'
        for i, event_name in enumerate(event_names):
            filters.append({
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [topic0_list[i], ]
            })

        events = [getattr(contract.events, en) for en in event_names]
        event_abis = [e().abi for e in events]
        address_exid = []
        for i, _filter in enumerate(filters):
            try:
                logs = self._web3.eth.getLogs(_filter)
            except ValueError as e:
                logger.error(f'get_dt_addresses_from_exchange_logs -> web3.eth.getLogs (filter={_filter}) failed: '
                             f'{e}..')
                logs = []

            if logs:
                args = args_list[i]
                for l in logs:
                    parsed_log = get_event_data(event_abis[i], l)
                    address_exid.extend([(parsed_log.args.get(arg, ''), add_0x_prefix(parsed_log.args.exchangeId.hex())) for arg in args])
                    # all_logs.append(parsed_log)

        return address_exid

    def get_dt_addresses_from_pool_logs(self, from_block, to_block=None):
        contract = BPool(None)
        event_names = ['LOG_JOIN', 'LOG_EXIT', 'LOG_SWAP']
        topic0_list = [self._get_event_signature(contract, en) for en in event_names]
        args_list = [('tokenIn',), ('tokenOut',), ('tokenIn', 'tokenOut')]
        filters = []
        to_block = to_block or 'latest'
        for i, event_name in enumerate(event_names):
            filters.append({
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [topic0_list[i],]
            })

        events = [getattr(contract.events, en) for en in event_names]
        event_abis = [e().abi for e in events]
        # all_logs = []
        addresses = []
        for i, _filter in enumerate(filters):
            try:
                logs = self._web3.eth.getLogs(_filter)
            except ValueError as e:
                logger.error(f'get_dt_addresses_from_pool_logs -> web3.eth.getLogs (filter={_filter}) failed: '
                             f'{e}..')
                logs = []

            if logs:
                args = args_list[i]
                for l in logs:
                    parsed_log = get_event_data(event_abis[i], l)
                    addresses.extend([(parsed_log.args.get(arg, ''), parsed_log.address) for arg in args])
                    # all_logs.append(parsed_log)

        addresses_and_pools = [(a, pool) if a and a.lower() != self._OCEAN else ('', pool) for (a, pool) in addresses]
        return addresses_and_pools

    def get_datatoken_pools(self, dt_address, from_block=0, to_block='latest'):
        contract = BPool(None)
        topic0 = self._get_event_signature(contract, 'LOG_JOIN')
        topic2 = f'0x000000000000000000000000{remove_0x_prefix(dt_address).lower()}'
        filter_params = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [topic0, None, topic2],
        }

        e = getattr(contract.events, 'LOG_JOIN')
        event_abi = e().abi
        logs = self._web3.eth.getLogs(filter_params)
        if not logs:
            return None

        pools = [get_event_data(event_abi, log).address for log in logs]
        return pools

    def _get_liquidity_and_price(self, pools, dt_address):
        _pool = pools[0]
        pool = BPool(_pool)
        dt_reserve = pool.getBalance(dt_address)
        ocn_reserve = pool.getBalance(self._checksum_ocean)

        # price = pool.getSpotPrice(self._checksum_ocean, dt_address)
        price = pool.calcInGivenOut(
            ocn_reserve,
            pool.getDenormalizedWeight(self._checksum_ocean),
            dt_reserve,
            pool.getDenormalizedWeight(dt_address),
            to_base_18(1.0),
            pool.getSwapFee()
        )
        return from_base_18(dt_reserve), from_base_18(ocn_reserve), from_base_18(price), _pool

    def _get_fixedrateexchange_price(self, dt_address, owner=None, exchange_id=None):
        fre = FixedRateExchange(self._addresses.get(FixedRateExchange.CONTRACT_NAME))
        if not exchange_id:
            assert owner is not None, 'owner is required when `exchange_id` is not given.'
            exchange_id = fre.generateExchangeId(
                self._checksum_ocean, dt_address, owner)

        price = fre.get_base_token_quote(exchange_id, to_base_18(1.0))
        supply = fre.contract_concise.getSupply(exchange_id)
        return from_base_18(price), from_base_18(supply)

    def get_all_pools(self):
        bfactory = BFactory(self._addresses.get(BFactory.CONTRACT_NAME))
        event_name = 'BPoolRegistered'
        event = getattr(bfactory.events, event_name)
        latest_block = self._web3.eth.blockNumber
        _from = self.bfactory_block
        chunk = 10000
        pools = []
        while _from < latest_block:
            event_filter = EventFilter(
                event_name,
                event,
                None,
                from_block=_from,
                to_block=_from+chunk-1
            )
            try:
                logs = event_filter.get_all_entries(max_tries=10)
                logs = sorted(logs, key=lambda l: l.blockNumber)
                pools.extend([l.args.bpoolAddress for l in logs])
            except ValueError as e:
                logger.error(f'get_all_pools BFactory {bfactory.address}, fromBlock {_from}, toBlock{_from+chunk-1}: {e}')
            _from += chunk

        return pools

    def do_update(self):
        did_prefix = 'did:op:'
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

        frexchange_address = self.ex_contract.address
        for asset in self._get_all_assets():
            did = asset['id']
            if not did.startswith(did_prefix):
                logger.warning(f'skipping price info update for asset {did} because the did is invalid.')
                continue

            dt_address = add_0x_prefix(did[prefix_len:])
            _dt_address = self._web3.toChecksumAddress(dt_address)
            dt_address = dt_address.lower()
            pools = dt_to_pool.get(dt_address, [])

            if not pools:
                owner = asset['proof'].get('creator')
                if not owner or not self._web3.isAddress(owner):
                    logger.warning(f'updating price info for datatoken {dt_address} failed, invalid owner from ddo.proof (owner={owner}).')
                    continue

                price, dt_supply = self._get_fixedrateexchange_price(_dt_address, owner)
                price_dict = {
                    'datatoken': dt_supply,
                    'ocean': 0.0,
                    'value': price,
                    'type': 'exchange',
                    'address': frexchange_address,
                    'pools': []
                }

            else:
                dt_reserve, ocn_reserve, price, pool_address = self._get_liquidity_and_price(pools, _dt_address)
                price_dict = {
                    'datatoken': dt_reserve,
                    'ocean': ocn_reserve,
                    'value': price,
                    'type': 'pool',
                    'address': pool_address,
                    'pools': pools
                }

            asset['price'] = price_dict
            asset['dataTokenInfo'] = get_datatoken_info(_dt_address)

            logger.info(f'updating price info for datatoken: {dt_address}, pools {pools}, price-info {price_dict}')
            self._oceandb.update(asset, did)

    def update_dt_assets_with_exchange_info(self, dt_address_exid):
        did_prefix = 'did:op:'
        dao = Dao(oceandb=self._oceandb)
        _dt_address_ex_list = []
        seen_exs = set()
        for address, exid in dt_address_exid:
            if not address or exid in seen_exs:
                continue

            seen_exs.add(exid)
            logger.info(f'updating price info for datatoken: {address}, exchangeId {exid}')
            did = did_prefix + remove_0x_prefix(address)
            try:
                asset = dao.get(did)
                _price_dict = asset.get('price', {})
                _pools = _price_dict.get('pools', [])
                if _price_dict.get('type') == 'pool' and _pools:
                    # skip if the asset has pools
                    continue

                _dt_address = self._web3.toChecksumAddress(address)
                price, dt_supply = self._get_fixedrateexchange_price(_dt_address, exchange_id=exid)
                price_dict = {
                    'datatoken': dt_supply,
                    'ocean': 0.0,
                    'value': price,
                    'type': 'exchange',
                    'address': self.ex_contract.address,
                    'pools': []
                }
                asset['price'] = price_dict
                asset['dataTokenInfo'] = get_datatoken_info(_dt_address)

                self._oceandb.update(asset, did)
                logger.info(f'updated price info: dt={address}, exchangeAddress={self.ex_contract.address}, '
                            f'exchangeId={exid}, price={asset["price"]}')
            except Exception as e:
                logger.error(f'updating datatoken assets price values from exchange contract: {e}')

    def update_dt_assets(self, dt_address_pool_list):
        did_prefix = 'did:op:'
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

        for address, pools in dt_to_pools.items():
            logger.info(f'updating price info for datatoken: {address}, pools {pools}')
            did = did_prefix + remove_0x_prefix(address)
            try:
                asset = dao.get(did)
                _price_dict = asset.get('price', {})
                _pools = _price_dict.get('pools', [])
                _dt_address = self._web3.toChecksumAddress(address)
                _pools.extend([p for p in pools if p not in _pools])

                dt_reserve, ocn_reserve, price, pool_address = self._get_liquidity_and_price(pools, _dt_address)
                price_dict = {
                    'datatoken': dt_reserve,
                    'ocean': ocn_reserve,
                    'value': price,
                    'type': 'pool',
                    'address': pool_address,
                    'pools': _pools
                }
                asset['price'] = price_dict
                asset['dataTokenInfo'] = get_datatoken_info(_dt_address)

                self._oceandb.update(asset, did)
                logger.info(f'updated price info: dt={address}, pool={pool_address}, price={asset["price"]}')
            except Exception as e:
                logger.error(f'updating datatoken assets price/liquidity values: {e}')

    def process_pool_events(self):
        try:
            last_block = self.get_last_processed_block()
        except Exception as e:
            logger.warning(f'exception thrown reading last_block from db: {e}')
            last_block = 0

        block = self._web3.eth.blockNumber
        if not block or not isinstance(block, int) or block <= last_block:
            return

        from_block = last_block
        logger.debug(f'from_block:{from_block}, current_block:{block}')
        ok = False
        try:
            dt_address_pool_list = self.get_dt_addresses_from_pool_logs(from_block=from_block, to_block=block)
            self.update_dt_assets(dt_address_pool_list)
            dt_address_exchange = self.get_dt_addresses_from_exchange_logs(from_block=from_block, to_block=block)
            self.update_dt_assets_with_exchange_info(dt_address_exchange)
            ok = True

        except Exception as e:
            logging.error(f'process_pool_events: {e}')

        finally:
            if ok and isinstance(block, int):
                self.store_last_processed_block(block)
