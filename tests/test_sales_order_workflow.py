"""Static regression checks for the quote-to-sales-order workflow slice."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "inventree_quote_generator"


def test_quote_tracks_one_generated_sales_order_without_order_migration_dependency():
    models = (PACKAGE_ROOT / "models.py").read_text(encoding="utf-8")
    migration = (PACKAGE_ROOT / "migrations" / "0003_quote_sales_order.py").read_text(
        encoding="utf-8"
    )

    assert "sales_order_id = models.PositiveIntegerField" in models
    assert "unique=True" in models
    assert "sales_order_reference = models.CharField" in models
    assert '("order",' not in migration


def test_conversion_is_explicit_pending_and_idempotent():
    workflow = (PACKAGE_ROOT / "workflow.py").read_text(encoding="utf-8")
    core = (PACKAGE_ROOT / "core.py").read_text(encoding="utf-8")
    template = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_editor.html"
    ).read_text(encoding="utf-8")

    assert "select_for_update()" in workflow
    assert "if locked_quote.sales_order_id:" in workflow
    assert "sales_order.issue_order" not in workflow
    assert "create-sales-order" in core
    assert "Create Sales Order" in template
    assert "It does not issue, ship, or invoice it." in template
