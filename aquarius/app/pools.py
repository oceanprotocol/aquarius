import json
import logging
import os

from flask import Blueprint, request, Response

from ocean_lib.config_provider import ConfigProvider
from ocean_lib.models.bpool import BPool
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.ocean.util import from_base_18

from aquarius.app.util import get_request_data

pools = Blueprint('pools', __name__)

logger = logging.getLogger(__name__)


@pools.route('/history/<poolAddress>', methods=['GET'])
def get_liquidity_history(poolAddress):
    """

    :param poolAddress:
    :return: json object with two keys: `ocean` and `datatoken`
      each has a list of datapoints sampled at specific time intervals from the pools liquidity history.
    """
    try:
        result = dict()
        ocean = Ocean(ConfigProvider.get_config())
        ocn_add_remove_list, dt_add_remove_list = ocean.pool.get_liquidity_history(poolAddress)
        pool = BPool(poolAddress)
        dt_address = ocean.pool.get_token_address(poolAddress, pool, validate=False)
        swap_fee = from_base_18(pool.getSwapFee())
        ocn_weight = from_base_18(pool.getDenormalizedWeight(ocean.OCEAN_address))
        dt_weight = from_base_18(pool.getDenormalizedWeight(dt_address))

        # numer = ov / ocn_weight
        # denom = dtv / dt_weight
        # ratio = numer / denom
        scale = 1.0 / (1.0 - swap_fee)
        # # price = ratio * scale
        weight_ratio = dt_weight / ocn_weight
        tot_ratio = weight_ratio * scale
        # p = ((ov / ocn_weight) / (dtv / dt_weight)) * (1.0 / (1.0 - swap_fee))
        # uint numer = bdiv(tokenBalanceIn, tokenWeightIn);
        # uint denom = bdiv(tokenBalanceOut, tokenWeightOut);
        # uint ratio = bdiv(numer, denom);
        # uint scale = bdiv(BONE, bsub(BONE, swapFee));
        # return  (spotPrice = bmul(ratio, scale));

        # build accumulated liquidity
        def get_accumulative_values(values_list):
            acc_values = [values_list[0]]
            for k, (v, t) in enumerate(values_list[1:]):
                acc_values.append((acc_values[k][0] + v, t))
            return acc_values

        accumulated_ocn_values = get_accumulative_values(ocn_add_remove_list)
        accumulated_dt_values = get_accumulative_values(dt_add_remove_list)

        _ocn_values = []
        _dt_values = []
        prices = []
        all_times = sorted({tup[1] for tup in (accumulated_dt_values + accumulated_ocn_values)})

        i = 0
        j = 0
        ocnv, ocnt = accumulated_ocn_values[i]
        dtv, dtt = accumulated_dt_values[j]
        for t in all_times:
            _v, _t = accumulated_ocn_values[i+1]
            if _t <= t:
                ocnv = _v
                i += 1

            _v, _t = accumulated_dt_values[j+1]
            if _t <= t:
                dtv = _v
                j += 1

            _ocn_values.append((ocnv, t))
            _dt_values.append((dtv, t))
            prices.append(((ocnv / dtv) * tot_ratio, t))

        result['oceanAddRemove'] = ocn_add_remove_list
        result['datatokenAddRemove'] = dt_add_remove_list
        result['oceanReserve'] = _ocn_values
        result['datatokenReserve'] = _dt_values
        result['oceanPrice'] = prices
        return Response(json.dumps(result), 200, content_type='application/json')
    except Exception as e:
        logger.error(f'pools/history/{poolAddress}: {str(e)}')
        return f'Get pool liquidity/price history failed: {str(e)}', 500


@pools.route('/liquidity/<poolAddress>', methods=['GET'])
def get_current_liquidity_stats(poolAddress):
    """

    :param poolAddress:
    :return:
    """
    try:
        data = get_request_data(request) or {}
        dt_address = data.get('datatokenAddress', None)
        from_block = data.get('fromBlock', None)
        to_block = data.get('toBlock', None)
        ocean = Ocean(ConfigProvider.get_config())
        pool_info = ocean.pool.get_short_pool_info(poolAddress, dt_address, from_block, to_block)
        return Response(json.dumps(pool_info), 200, content_type='application/json')
    except Exception as e:
        logger.error(f'pools/liquidity/{poolAddress}: {str(e)}')
        return f'Get pool current liquidity stats failed: {str(e)}', 500


@pools.route('/user/<userAddress>', methods=['GET'])
def get_user_balances(userAddress):
    """

    :param userAddress:
    :return:
    """
    try:
        data = get_request_data(request) or {}
        from_block = data.get('fromBlock', int(os.getenv('BFACTORY_BLOCK', 0)))
        ocean = Ocean(ConfigProvider.get_config())
        result = ocean.pool.get_user_balances(userAddress, from_block)
        return Response(json.dumps(result), 200, content_type='application/json')
    except Exception as e:
        logger.error(f'pools/user/{userAddress}: {str(e)}')
        return f'Get pool user balances failed: {str(e)}', 500
