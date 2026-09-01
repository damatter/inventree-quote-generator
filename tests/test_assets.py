"""Packaging and remote-component smoke checks."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "inventree_quote_generator"


def test_remote_ui_exports_all_inventree_entry_points():
    script = (PACKAGE_ROOT / "assets" / "ui.js").read_text(encoding="utf-8")
    assert "export function openQuoteWorkspace" in script
    assert "export function renderQuoteShortcut" in script
    assert "export function renderPartQuotePanel" in script


def test_site_templates_and_assets_are_present():
    assert (PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_list.html").is_file()
    assert (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_editor.html"
    ).is_file()
    assert (PACKAGE_ROOT / "assets" / "site.css").is_file()
    assert (PACKAGE_ROOT / "assets" / "site.js").is_file()
    assert not (PACKAGE_ROOT / "static").exists()
