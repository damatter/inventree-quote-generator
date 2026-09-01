"""Pure unit tests for customer quantity-break selection."""

from decimal import Decimal

from inventree_quote_generator.pricing import select_applicable_break


def test_highest_applicable_quantity_break_is_selected():
    breaks = [
        (1, Decimal("1"), Decimal("12.50")),
        (2, Decimal("10"), Decimal("10.00")),
        (3, Decimal("25"), Decimal("8.75")),
    ]

    assert select_applicable_break(breaks, Decimal("24")) == breaks[1]


def test_exact_quantity_break_is_selected():
    breaks = [
        (1, Decimal("1"), Decimal("12.50")),
        (2, Decimal("10"), Decimal("10.00")),
    ]

    assert select_applicable_break(breaks, Decimal("10")) == breaks[1]


def test_quantity_below_first_break_requires_manual_price():
    breaks = [(1, Decimal("5"), Decimal("12.50"))]

    assert select_applicable_break(breaks, Decimal("4")) is None
