import pytest
from src. discounts import discount_rate, discounted_total

@pytest.mark.parametrize(("subtotal", "expected"), [(0,0.0),(99.99,0.0),(100,0.05),(499.99,0.05),(500,0.10),(750,0.10)])
def test_discount_rate_boundaries(subtotal, expected):
    assert discount_rate(subtotal) == expected

def test_discounted_total():
    assert discounted_total(100.0) == 95.0
