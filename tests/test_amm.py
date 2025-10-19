import pytest

from engine.amm import cpmm_price_after_trade


def test_cpmm_invariant():
    result = cpmm_price_after_trade(1000, 1000, 10, 30, direction="buy")
    assert pytest.approx(result.new_reserve_in * result.new_reserve_out, rel=1e-3) == 1000 * 1000
    assert result.price > 0


def test_slippage_sign():
    result = cpmm_price_after_trade(1000, 1000, 50, 30, direction="buy")
    assert result.slip_bps > 0
