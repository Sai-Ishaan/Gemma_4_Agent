### Discount policy for Phase 0 Mock Repo

def discount_rate(subtotal: float)->float:
    if subtotal<=100:
        return 0.0 ## 0% below 100
    if subtotal < 500:
        return 0.05 ## 5% from 100 to <500
    return 0.10 ## 10% from 500 and above

def discounted_total(subtotal: float)-> float:
    return round(subtotal * (1.0 -discount_rate(subtotal)), 2)