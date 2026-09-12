class CartTotal:
    """Represents calculated cart total with subtotal and tax amounts."""

    def __init__(self, subtotal: float, tax: float):
        self.subtotal = subtotal
        self.tax = tax


def calculate_total(cart):
    """Calculates subtotal and tax for given items in cart."""
    subtotal = sum(item["price"] for item in cart)
    tax = round(subtotal * 0.08, 2)
    # Changed from dict return {"subtotal": subtotal, "tax": tax} to CartTotal object
    return CartTotal(subtotal, tax)
