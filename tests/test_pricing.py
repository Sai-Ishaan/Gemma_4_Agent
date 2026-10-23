import pytest
from src.pricing import price_order

def test_order_price_applies_discount():
    assert price_order(25.0, 4) == 95.0

def test_order_price_without_discount():
    assert price_order(10.0, 2) == 20.0

@pytest.mark.parametrize(("price", "quantity"), [(-1,2),(1,-2)])
def test_negative_inputs_rejected(price, quantity):
    with pytest.raises(ValueError): price_order(price, quantity)
