## Inventory helpers for dependency tasks

def available_quantity(on_hand: int, reserved: int)-> int:
    ### Return sellable inventory after reservations
    if on_hand<0 or reserved<0:
        raise ValueError("quantities must be non-negative!")
    return max(0, on_hand - reserved)


def can_fulfill(on_hand: int, reserved: int, requested: int)-> bool:
    ## return whether inventory that can be sold can fulfill a request
    if requested<0:
        raise ValueError("Requested must be non-negative units!")
    return available_quantity(on_hand, reserved)>= requested