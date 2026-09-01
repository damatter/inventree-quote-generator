"""Bridge quote line items to the separate customer-pricing plugin."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResolvedPrice:
    """A customer-specific price result safe to snapshot on a quote."""

    found: bool
    unit_price: Decimal | None = None
    currency: str = ""
    price_break_id: int | None = None
    source: str = ""
    message: str = ""


def select_applicable_break(
    breaks: Iterable[tuple[int, Decimal, Decimal]], quantity: Decimal
) -> tuple[int, Decimal, Decimal] | None:
    """Choose the highest minimum quantity which does not exceed the requested quantity."""

    applicable = [item for item in breaks if item[1] <= quantity]
    return max(applicable, key=lambda item: item[1]) if applicable else None


def resolve_customer_price(customer_id: int, part_id: int, quantity: Decimal) -> ResolvedPrice:
    """Resolve a quantity break from inventree-customer-pricing, if available."""

    from django.apps import apps

    try:
        price_list_model = apps.get_model(
            "inventree_customer_pricing", "CustomerPriceList", require_ready=True
        )
    except LookupError:
        return ResolvedPrice(
            found=False,
            message="Customer Pricing is not installed or active; enter a manual price.",
        )

    price_list = (
        price_list_model.objects.filter(
            part_id=part_id,
            customer_id=customer_id,
            active=True,
        )
        .prefetch_related("breaks")
        .first()
    )
    if price_list is None:
        return ResolvedPrice(
            found=False,
            message="No active price list exists for this customer and part.",
        )

    selected = select_applicable_break(
        ((item.pk, item.quantity, item.price) for item in price_list.breaks.all()),
        quantity,
    )
    if selected is None:
        return ResolvedPrice(
            found=False,
            currency=price_list.currency,
            message="No quantity break applies at this quantity.",
        )

    break_id, minimum_quantity, price = selected
    return ResolvedPrice(
        found=True,
        unit_price=price,
        currency=price_list.currency,
        price_break_id=break_id,
        source=f"Customer price break at quantity {format(minimum_quantity, 'f')}",
        message="Customer-specific price applied.",
    )
