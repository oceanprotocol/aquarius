

# build accumulated liquidity
def get_accumulative_values(values_list):
    acc_values = [values_list[0]]
    n = 0
    for k, (v, t) in enumerate(values_list[1:]):
        if acc_values[n][1] == t:
            acc_values[n] = (acc_values[n][0] + v, t)
        else:
            acc_values.append((acc_values[n][0] + v, t))
            n += 1
    return acc_values


def build_liquidity_and_price_history(ocn_liquidity_changes, dt_liquidity_changes, ocn_weight, dt_weight, swap_fee):
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

    accumulated_ocn_values = get_accumulative_values(ocn_liquidity_changes)
    accumulated_dt_values = get_accumulative_values(dt_liquidity_changes)

    _ocn_values = []
    _dt_values = []
    prices = []
    all_times = sorted({tup[1] for tup in (accumulated_dt_values + accumulated_ocn_values)})

    i = 0
    j = 0
    ocnv, ocnt = accumulated_ocn_values[i]
    dtv, dtt = accumulated_dt_values[j]
    ocn_l = len(accumulated_ocn_values)
    dt_l = len(accumulated_dt_values)
    assert ocnt == dtt, 'The first timestamp does not match between ocean and datatoken liquidity.'
    assert all_times[0] == ocnt, ''

    for t in all_times:
        if (i+1) < ocn_l:
            _v, _t = accumulated_ocn_values[i + 1]
            if _t <= t:
                i += 1
                ocnv = _v

        if (j+1) < dt_l:
            _v, _t = accumulated_dt_values[j + 1]
            if _t <= t:
                j += 1
                dtv = _v

        _ocn_values.append((ocnv, t))
        _dt_values.append((dtv, t))
        prices.append(((ocnv / dtv) * tot_ratio, t))

    return _ocn_values, _dt_values, prices
