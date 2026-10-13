import pytest

from app.core.money import calculate_total_minor


@pytest.mark.parametrize(
    ("unit_price_minor", "quantity", "expected_total"),
    [
        (10_500, 100, 1_050_000),
        (101, 0.5, 51),
        (101, 1.5, 152),
        (10_000, 0, 0),
    ],
)
def test_calculate_total_minor_rounds_to_nearest_cent(
    unit_price_minor: int,
    quantity: int | float,
    expected_total: int,
):
    assert calculate_total_minor(unit_price_minor, quantity) == expected_total


def test_calculate_total_minor_rejects_non_finite_quantity():
    with pytest.raises(ValueError, match="finite"):
        calculate_total_minor(100, float("nan"))
