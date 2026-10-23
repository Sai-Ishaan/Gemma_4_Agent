##Order pricing depends on the discount policy
from src.discounts import discounted_total

def price_order(unit_price: float, quantity: int) -> float:
    ##Calculate discounted order total.
    if unit_price < 0:
        raise ValueError("unit_price must be non-negative")
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    return discounted_total(unit_price * quantity)
