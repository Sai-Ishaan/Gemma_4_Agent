import pytest
from src.formatting import format_currency

def test_currency_format():
    assert format_currency(12.5, "usd") == "USD 12.50"

def test_invalid_currency_rejected():
    with pytest.raises(ValueError): format_currency(12.5, "US")
