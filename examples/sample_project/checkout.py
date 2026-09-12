from payment import process_payment


def checkout(cart, user):
    """Orchestrates order checkout."""
    card = user.get("payment_card")
    payment_result = process_payment(cart, card)
    return {
        "order_status": "COMPLETED",
        "payment": payment_result,
    }
