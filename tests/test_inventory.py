import pytest
from src.inventory import available_quantity, can_fulfill

def test_available_quantity():
    assert available_quantity(10,3) == 7
    assert available_quantity(2,5) == 0

def test_can_fulfill():
    assert can_fulfill(10,3,7) is True
    assert can_fulfill(10,3,8) is False

def test_negative_inventory_rejected():
    with pytest.raises(ValueError): available_quantity(-1,0)
