import logging
import os
import time
from threading import Thread

from eth_utils import add_0x_prefix
from eth_utils import remove_0x_prefix
from ocean_lib.models.bfactory import BFactory
from ocean_lib.models.bpool import BPool
from ocean_lib.models.fixed_rate_exchange import FixedRateExchange
from ocean_lib.ocean.util import from_base_18, to_base_18
from ocean_lib.web3_internal.event_filter import EventFilter
from web3.utils.events import get_event_data

from aquarius.events.util import prepare_contracts

logger = logging.getLogger(__name__)


class MetadataUpdater:
    def __init__(self, oceandb, web3, config):
        self._oceandb = oceandb
        self._web3 = web3
        self._config = config

        self._addresses = prepare_contracts(self._web3, self._config)
        self._checksum_ocean = self._addresses.get('Ocean')
        self._OCEAN = self._checksum_ocean.lower()

        self._last_block = int(os.getenv('LAST_POOL_BLOCK', 0))
        if self._last_block == 0:
            self._last_block = int(os.getenv('BFACTORY_BLOCK', 0))

        self._is_on = False
        default_quiet_time = 60#3600
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
        while True:
            try:
                if not self._is_on:
                    return

                self.do_update()

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
        dt_reserve = ocn_reserve = prices = 0
        for pool_address in pools:
            pool = BPool(pool_address)
            dt_reserve += pool.getBalance(dt_address)
            ocn_reserve += pool.getBalance(self._checksum_ocean)

            prices += pool.getSpotPrice(self._checksum_ocean, dt_address)

        price = int(prices / len(pools))
        return dt_reserve, ocn_reserve, price

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
        _from = self._last_block
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
                asset['dtBalance'] = 0
                asset['OceanBalance'] = 0
                asset['dtPrice'] = from_base_18(price)

            else:
                dt_reserve, ocn_reserve, price = self._get_liquidity_and_price(pools, _dt_address)
                asset['dtBalance'] = from_base_18(dt_reserve)
                asset['OceanBalance'] = from_base_18(ocn_reserve)
                asset['dtPrice'] = from_base_18(price)

            self._oceandb.update(asset, did)
