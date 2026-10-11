def calculate_total(price: float, tax: float) -> float:
    if price < 0:
        raise ValueError("Price cannot be negative")
    return price * (1.0 + tax)
