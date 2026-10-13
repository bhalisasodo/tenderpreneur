from decimal import Decimal, ROUND_HALF_UP


def calculate_total_minor(unit_price_minor: int, quantity: int | float) -> int:
    """Multiply a minor-unit rate by a quantity and round the result to a minor unit."""
    quantity_decimal = Decimal(str(quantity))
    if not quantity_decimal.is_finite():
        raise ValueError("Quantity must be a finite number.")
    return int(
        (Decimal(unit_price_minor) * quantity_decimal).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )
