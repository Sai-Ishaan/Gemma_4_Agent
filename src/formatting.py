### Formatting helper
##Acts as an unrelated file 
def format_currency(amount: float,currency: str="USD") ->str:
    if not currency or not currency.isalpha() or len(currency) !=3:
        raise ValueError("Currency must be a 3 letter code!!")
    return f"{currency.upper()} {amount:.2f}"