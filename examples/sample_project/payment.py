from cart import calculate_total


def process_payment(cart, card_info):
    """Processes payment for the items in the cart."""
    total = calculate_total(cart)
    # Regression: Still accesses total via dictionary subscript syntax
    tax = total["tax"]
    subtotal = total["subtotal"]
    charge_amount = subtotal + tax
    return {
        "status": "APPROVED",
        "charged": charge_amount,
        "tax": tax,
    }
