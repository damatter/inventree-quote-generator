"""Create deterministic CSV files for the Windows Sage Bridge."""

from __future__ import annotations

import csv
import re
from io import StringIO

SAGE_HEADERS = (
    "OrderNumber",
    "Customer",
    "TransactionType",
    "Description",
    "Quantity",
    "UnitPrice",
    "RevenueAccount",
    "TaxCode",
    "InvoiceDate",
    "ShipDate",
)


class SageExportError(ValueError):
    """Raised when a quote is not safe to send to the Sage Bridge."""


def _text(value) -> str:
    return str(value or "").strip()


def _number(value) -> str:
    return format(value, "f")


def _line_description(line) -> str:
    part_number = _text(getattr(line, "part_number", ""))
    description = _text(getattr(line, "description", ""))
    if part_number and description and part_number.casefold() != description.casefold():
        return f"{part_number} - {description}"
    return part_number or description


def _quote_lines(quote):
    related = quote.line_items
    return list(related.all() if hasattr(related, "all") else related)


def render_sage_csv(quote) -> bytes:
    """Return a validated UTF-8 CSV accepted by Sage Bridge."""

    if _text(getattr(quote, "status", "")) != "accepted":
        raise SageExportError("Mark the quote Accepted and save it before exporting to Sage.")

    customer = _text(getattr(quote, "sage_customer_name", "")) or _text(
        getattr(quote, "customer_name", "")
    )
    if not customer:
        customer = _text(getattr(getattr(quote, "customer", None), "name", ""))
    reference = _text(getattr(quote, "sage_reference", "")) or _text(
        getattr(quote, "quote_number", "")
    )
    transaction_type = _text(getattr(quote, "sage_transaction_type", ""))
    account = _text(getattr(quote, "sage_revenue_account", ""))
    tax_code = _text(getattr(quote, "sage_tax_code", ""))
    invoice_date = getattr(quote, "invoice_date", None)
    ship_date = getattr(quote, "ship_date", None)

    errors = []
    if not customer:
        errors.append("Enter the exact Sage customer name.")
    if not reference:
        errors.append("Enter a Sage transaction number.")
    if transaction_type not in {"Sales Invoice", "Sales Order"}:
        errors.append("Choose Sales Invoice or Sales Order.")
    if not account:
        errors.append("Enter the Sage revenue account.")
    if invoice_date is None:
        errors.append("Enter the invoice/order date.")
    if ship_date is None:
        errors.append("Enter the ship date.")

    rows = []
    for position, line in enumerate(_quote_lines(quote), start=1):
        description = _line_description(line)
        quantity = getattr(line, "quantity", None)
        unit_price = getattr(line, "unit_price", None)
        line_errors = []
        if not description:
            line_errors.append("description")
        if quantity is None or quantity <= 0:
            line_errors.append("quantity greater than zero")
        if unit_price is None or unit_price < 0:
            line_errors.append("unit price")
        if line_errors:
            errors.append(f"Line {position} needs: {', '.join(line_errors)}.")
            continue
        rows.append(
            (
                reference,
                customer,
                transaction_type,
                description,
                _number(quantity),
                _number(unit_price),
                account,
                tax_code,
                invoice_date.isoformat() if invoice_date else "",
                ship_date.isoformat() if ship_date else "",
            )
        )

    if not rows:
        errors.append("Add at least one complete line item.")
    if errors:
        raise SageExportError(" ".join(errors))

    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(SAGE_HEADERS)
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def sage_csv_filename(reference: str) -> str:
    """Return a stable, filesystem-safe Sage handoff filename."""

    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", _text(reference)).strip("._")
    return f"{stem or 'quote'}_sage.csv"
