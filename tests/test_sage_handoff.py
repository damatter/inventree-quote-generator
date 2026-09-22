"""Regression checks for the direct quote-to-Sage handoff."""

import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from inventree_quote_generator.sage import SageExportError, render_sage_csv

PACKAGE_ROOT = Path(__file__).parents[1] / "inventree_quote_generator"


def quote_fixture(**overrides):
    values = {
        "status": "accepted",
        "quote_number": "QT-2026-0005",
        "customer_name": "TEST CUSTOMER",
        "customer": SimpleNamespace(name="TEST CUSTOMER"),
        "sage_customer_name": "",
        "sage_reference": "",
        "sage_transaction_type": "Sales Invoice",
        "sage_revenue_account": "4220",
        "sage_tax_code": "H",
        "invoice_date": date(2026, 9, 22),
        "ship_date": date(2026, 9, 23),
        "line_items": [
            SimpleNamespace(
                part_number="TESTPART",
                description="Test part",
                quantity=Decimal("2"),
                unit_price=Decimal("10.00"),
            ),
            SimpleNamespace(
                part_number="SECOND",
                description="Second part",
                quantity=Decimal("1"),
                unit_price=Decimal("5.50"),
            ),
        ],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_export_contains_every_quote_line_and_sage_field():
    text = render_sage_csv(quote_fixture()).decode("utf-8-sig")
    rows = list(csv.DictReader(StringIO(text)))

    assert len(rows) == 2
    assert rows[0] == {
        "OrderNumber": "QT-2026-0005",
        "Customer": "TEST CUSTOMER",
        "TransactionType": "Sales Invoice",
        "Description": "TESTPART - Test part",
        "Quantity": "2",
        "UnitPrice": "10.00",
        "RevenueAccount": "4220",
        "TaxCode": "H",
        "InvoiceDate": "2026-09-22",
        "ShipDate": "2026-09-23",
    }
    assert rows[1]["OrderNumber"] == rows[0]["OrderNumber"]
    assert rows[1]["Description"] == "SECOND - Second part"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"status": "sent"}, "Mark the quote Accepted"),
        ({"sage_revenue_account": ""}, "revenue account"),
        ({"invoice_date": None}, "invoice/order date"),
        ({"ship_date": None}, "ship date"),
        ({"line_items": []}, "complete line item"),
    ],
)
def test_export_rejects_incomplete_or_unaccepted_quotes(overrides, message):
    with pytest.raises(SageExportError, match=message):
        render_sage_csv(quote_fixture(**overrides))


def test_ui_uses_direct_sage_export_not_native_sales_order_creation():
    core = (PACKAGE_ROOT / "core.py").read_text(encoding="utf-8")
    editor = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_editor.html"
    ).read_text(encoding="utf-8")
    quote_list = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_list.html"
    ).read_text(encoding="utf-8")

    assert "sage-export" in core
    assert "create-sales-order" not in core
    assert "Download Sage file" in editor
    assert "Download Sage file" in quote_list
    assert "Create Sales Order" not in editor + quote_list
