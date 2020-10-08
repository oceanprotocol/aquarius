import logging
import os
import time
from threading import Thread
import traceback

from eth_utils import add_0x_prefix
from eth_utils import remove_0x_prefix
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.ocean.util import from_base_18, to_base_18
from ocean_lib.web3_internal.event_filter import EventFilter
from web3.utils.events import get_event_data

from aquarius.app.dao import Dao
from aquarius.events.util import prepare_contracts

logger = logging.getLogger(__name__)


class MetadataUpdater:
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

        self.bfactory_block = int(os.getenv('BFACTORY_BLOCK', 0))
        self._do_first_update = True
        try:
            self.get_last_processed_block()
            self._do_first_update = False
        except Exception:
            self.store_last_processed_block(self.bfactory_block)

        self._is_on = False
        default_quiet_time = 20
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
        self._oceandb.update(record, 'pool_events_last_block')

    def get_dt_addresses_from_pool_logs(self, from_block, to_block='latest'):
        contract = BPool(None)
        event_names = ['LOG_JOIN', 'LOG_EXIT', 'LOG_SWAP']
        topic0_list = [self._get_event_signature(contract, en) for en in event_names]
        args_list = [('tokenIn',), [('tokenOut',)], [('tokenIn', 'tokenOut')]]
        filters = []
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
        _pool = None
        low_price = -1
        for pool_address in pools:
            pool = BPool(pool_address)
            price = pool.getSpotPrice(self._checksum_ocean, dt_address)
            if low_price < 0 or price < low_price:
                low_price = price
                _pool = pool_address

        price = low_price
        pool = BPool(_pool)
        dt_reserve = pool.getBalance(dt_address)
        ocn_reserve = pool.getBalance(self._checksum_ocean)
        return dt_reserve, ocn_reserve, price, _pool

    def _get_fixedrateexchange_price(self, dt_address, owner):
        fre = FixedRateExchange(self._addresses.get(FixedRateExchange.CONTRACT_NAME))
        exchange_id = fre.generateExchangeId(
            self._checksum_ocean, dt_address, owner)
        return fre.get_base_token_quote(exchange_id, to_base_18(1.0))

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

        frexchange_address = self._addresses.get(FixedRateExchange.CONTRACT_NAME)
        for asset in self._get_all_assets():
            did = asset['id']
            if not did.startswith(did_prefix):
                continue

            dt_address = add_0x_prefix(did[prefix_len:])
            _dt_address = self._web3.toChecksumAddress(dt_address)
            dt_address = dt_address.lower()
            pools = dt_to_pool.get(dt_address, [])

            if not pools:
                owner = asset['proof'].get('creator')
                if not owner or not self._web3.isAddress(owner):
                    continue

                price = self._get_fixedrateexchange_price(_dt_address, owner)
                price_dict = {
                    'datatoken': 0.0,
                    'ocean': 0.0,
                    'value': from_base_18(price),
                    'type': 'exchange',
                    'address': frexchange_address
                }

            else:
                dt_reserve, ocn_reserve, price, pool_address = self._get_liquidity_and_price(pools, _dt_address)
                price_dict = {
                    'datatoken': from_base_18(dt_reserve),
                    'ocean': from_base_18(ocn_reserve),
                    'value': from_base_18(price),
                    'type': 'pool',
                    'address': pool_address
                }

            asset['price'] = price_dict
            self._oceandb.update(asset, did)

    def update_dt_assets(self, dt_address_pool_list):
        did_prefix = 'did:op:'
        dao = Dao(oceandb=self._oceandb)
        _dt_address_pool_list = []
        for address, pool_address in dt_address_pool_list:
            if not address:
                address = BPool(pool_address).getCurrentTokens()[0]

            _dt_address_pool_list.append((address, pool_address))

        dt_to_pools = {a: [] for a, p in _dt_address_pool_list}
        for address, pool_address in _dt_address_pool_list:
            dt_to_pools[address].append(pool_address)

        for address, pools in dt_to_pools.items():
            did = did_prefix + remove_0x_prefix(address)
            try:
                asset = dao.get(did)
                _dt_address = self._web3.toChecksumAddress(address)

                dt_reserve, ocn_reserve, price, pool_address = self._get_liquidity_and_price(pools, _dt_address)
                price_dict = {
                    'datatoken': from_base_18(dt_reserve),
                    'ocean': from_base_18(ocn_reserve),
                    'value': from_base_18(price),
                    'type': 'pool',
                    'address': pool_address
                }
                asset['price'] = price_dict

                self._oceandb.update(asset, did)
            except Exception as e:
                logger.error(f'updating datatoken assets price/liquidity values: {e}')

    def process_pool_events(self):
        last_block = self.get_last_processed_block()
        block = self._web3.eth.blockNumber
        ok = False
        try:
            dt_address_pool_list = self.get_dt_addresses_from_pool_logs(from_block=last_block+1, to_block=block)
            self.update_dt_assets(dt_address_pool_list)
            ok = True

        except Exception as e:
            logging.error(f'process_pool_events: {e}')
            traceback.print_exc()

        finally:
            if ok and isinstance(block, int):
                self.store_last_processed_block(block)
