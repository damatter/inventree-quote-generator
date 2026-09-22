"""Quote-to-order workflow services.

InvenTree model imports deliberately remain inside the public function so plugin
discovery does not load application models before Django is ready.
"""

from __future__ import annotations


def _line_description(line) -> str:
    """Build a readable, bounded description for an extra sales-order line."""

    values = [value.strip() for value in (line.part_number, line.description) if value.strip()]
    return " — ".join(values)[:250]


def _part_line_notes(line) -> str:
    """Preserve the quote's description snapshot on a part-backed order line."""

    values = [value.strip() for value in (line.description, line.notes) if value.strip()]
    return " | ".join(values)[:500]


def _validate_quote(quote, lines) -> None:
    from django.core.exceptions import ValidationError

    errors = []
    if quote.status != quote.Status.ACCEPTED:
        errors.append("Mark the quote Accepted and save it before creating a sales order.")
    if not lines:
        errors.append("Add at least one line item before creating a sales order.")

    quote_currency = (quote.currency or "CAD").upper()
    for position, line in enumerate(lines, start=1):
        label = line.part_number or line.description or f"line {position}"
        if line.quantity is None or line.quantity <= 0:
            errors.append(f"{label}: quantity must be greater than zero.")
        if line.unit_price is None:
            errors.append(f"{label}: enter a unit price.")
        line_currency = (line.currency or quote_currency).upper()
        if line_currency != quote_currency:
            errors.append(f"{label}: currency must match the quote ({quote_currency}).")
        if line.part_id and not line.part.salable:
            errors.append(f"{label}: mark the InvenTree part as salable first.")
        if not line.part_id and not (line.part_number.strip() or line.description.strip()):
            errors.append(f"Line {position}: enter a part number or description.")

    if errors:
        raise ValidationError(errors)


def convert_quote_to_sales_order(quote, user):
    """Create one pending native SalesOrder from an accepted quote.

    Returns ``(sales_order, created)``. The quote row is locked during the
    transaction, so retries and double-clicks cannot create duplicate orders.
    """

    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.utils import timezone
    from djmoney.money import Money
    from order.models import SalesOrder, SalesOrderExtraLine, SalesOrderLineItem

    from .models import Quote

    with transaction.atomic():
        locked_quote = Quote.objects.select_for_update().select_related("customer").get(pk=quote.pk)

        if locked_quote.sales_order_id:
            existing = SalesOrder.objects.filter(pk=locked_quote.sales_order_id).first()
            if existing is not None:
                return existing, False
            raise ValidationError(
                "The linked sales order no longer exists. An administrator must review "
                "the quote before another order is created."
            )

        lines = list(locked_quote.line_items.select_related("part").all())
        _validate_quote(locked_quote, lines)

        description = f"Accepted quote {locked_quote.quote_number}"
        if locked_quote.subject.strip():
            description = f"{description} — {locked_quote.subject.strip()}"

        sales_order = SalesOrder(
            customer=locked_quote.customer,
            description=description[:250],
            created_by=user,
            order_currency=(locked_quote.currency or "CAD").upper(),
        )
        sales_order.full_clean()
        sales_order.save()

        for position, quote_line in enumerate(lines, start=1):
            currency = (quote_line.currency or locked_quote.currency or "CAD").upper()
            price = Money(quote_line.unit_price, currency)
            common = {
                "order": sales_order,
                "quantity": quote_line.quantity,
                "line": str(position),
                "reference": quote_line.part_number[:100],
            }

            if quote_line.part_id:
                order_line = SalesOrderLineItem(
                    **common,
                    part=quote_line.part,
                    sale_price=price,
                    notes=_part_line_notes(quote_line),
                )
            else:
                order_line = SalesOrderExtraLine(
                    **common,
                    description=_line_description(quote_line),
                    price=price,
                    notes=quote_line.notes[:500],
                )

            order_line.full_clean()
            order_line.save()

        locked_quote.sales_order_id = sales_order.pk
        locked_quote.sales_order_reference = sales_order.reference
        locked_quote.converted_at = timezone.now()
        locked_quote.converted_by = user
        locked_quote.save(
            update_fields=[
                "sales_order_id",
                "sales_order_reference",
                "converted_at",
                "converted_by",
                "updated",
            ]
        )

    return sales_order, True
