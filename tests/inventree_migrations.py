"""Exercise real upgrade histories on a disposable native InvenTree database."""

import os
from datetime import date
from decimal import Decimal

from company.models import Company
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from plugin.registry import registry

from inventree_quote_generator.pdf import quote_document_from_model, render_quote_pdf
from inventree_quote_generator.sage import render_sage_csv

# This script deliberately rolls back historical schema on TEST DATABASES ONLY.
assert os.environ.get("QUOTE_MIGRATION_TEST") == "1"
assert str(connection.settings_dict["NAME"]) in (
    "/tmp/quote-migrations.sqlite3", "quote_migrations_test"
)

APP = "inventree_quote_generator"
BASE = (APP, "0002_quote_letterhead")
RENAME = (APP, "0003_rename_inventree_q_status_1d39aa_idx_"
          "inventree_q_status_caae15_idx_and_more")
SAGE = (APP, "0004_quote_sage_handoff")
LATEST = (APP, "0005_merge_quote_indexes")
plugin = registry.get_plugin("quote-generator", active=True)
assert plugin is not None
customer = Company.objects.create(name="Migration test customer", is_customer=True)


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.check_consistent_history(connection)
    assert not executor.loader.detect_conflicts()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


def index_names():
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, f"{APP}_quote")


# The preceding normal migrate command already proves a clean installation.
assert LATEST in MigrationExecutor(connection).loader.applied_migrations
for case, (label, starting_targets) in enumerate((
    ("old letterhead release", [BASE]),
    ("server index branch", [RENAME]),
    ("published Sage release", [SAGE]),
    ("both branches already applied", [RENAME, SAGE]),
), start=1):
    migrate([BASE])
    historical = migrate(starting_targets)
    Quote = historical.get_model(APP, "Quote")
    Line = historical.get_model(APP, "QuoteLineItem")
    quote = Quote.objects.create(
        customer_id=customer.pk, customer_name="Saved customer snapshot",
        quote_number=f"MIGRATION-{case}",
        subject="Existing quote", company_name="Original letterhead", currency="CAD",
    )
    line = Line.objects.create(
        quote_id=quote.pk, quantity=Decimal("2"), unit_price=Decimal("12.50"),
        description="Preserved line", part_number="OEM-42", currency="CAD",
    )
    if SAGE in starting_targets:
        Quote.objects.filter(pk=quote.pk).update(
            sage_export_count=7, sage_reference="SAGE-KEEP", sales_order_id=9000 + quote.pk,
            sales_order_reference="SO-KEEP",
        )
    before_quote = Quote.objects.values().get(pk=quote.pk)
    before_line = Line.objects.values().get(pk=line.pk)
    indexes_before = set(index_names())
    if starting_targets == [RENAME, SAGE]:
        plan = MigrationExecutor(connection).migration_plan([LATEST])
        assert [(m.name, backward) for m, backward in plan] == [(LATEST[1], False)]
        assert plan[0][0].operations == []

    current = migrate([LATEST])
    Quote = current.get_model(APP, "Quote")
    Line = current.get_model(APP, "QuoteLineItem")
    after_quote = Quote.objects.values().get(pk=quote.pk)
    assert {k: after_quote[k] for k in before_quote} == before_quote, label
    assert Line.objects.values().get(pk=line.pk) == before_line, label
    indexes = index_names()
    for name, columns in (
        ("inventree_q_status_caae15_idx", ["status", "issue_date"]),
        ("inventree_q_custome_eec6d5_idx", ["customer_id", "issue_date"]),
    ):
        assert indexes[name]["columns"] == columns
    assert "inventree_q_status_1d39aa_idx" not in indexes
    assert "inventree_q_custome_77443f_idx" not in indexes
    if starting_targets == [RENAME, SAGE]:
        assert set(indexes) == indexes_before
    assert MigrationExecutor(connection).migration_plan([LATEST]) == []
    print("UPGRADE_PASS", label)

# Exercise the actual live model against the fully upgraded schema.
from inventree_quote_generator.models import Quote as LiveQuote  # noqa: E402

sample = LiveQuote.objects.get(pk=quote.pk)
sample.status = "accepted"
sample.invoice_date = sample.ship_date = date(2026, 10, 1)
sample.sage_revenue_account = "4220"
sample.save()
pdf = render_quote_pdf(quote_document_from_model(sample, plugin))
assert pdf.startswith(b"%PDF") and len(pdf) > 1000
csv = render_sage_csv(sample).decode("utf-8-sig")
assert "OEM-42 - Preserved line" in csv and "12.50" in csv
sample.refresh_from_db()
assert sample.sage_export_count == 7 and sample.sage_reference == "SAGE-KEEP"
call_command("makemigrations", APP, check=True, dry_run=True, interactive=False)
call_command("migrate", check=True, interactive=False)
print("NATIVE_QUOTE_PASS", connection.vendor, "PDF", len(pdf), "Sage CSV", len(csv))
