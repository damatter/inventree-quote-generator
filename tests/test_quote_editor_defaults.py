"""Regression checks for new-quote defaults and the searchable part picker."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parents[1] / "inventree_quote_generator"


def test_new_quote_defaults_override_empty_model_values():
    source = (PACKAGE_ROOT / "forms.py").read_text(encoding="utf-8")

    assert "self.initial.update(defaults)" in source
    assert "self.fields[name].initial = value" not in source


def test_line_item_uses_search_input_instead_of_full_select_menu():
    form_source = (PACKAGE_ROOT / "forms.py").read_text(encoding="utf-8")
    template = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "_line_item.html"
    ).read_text(encoding="utf-8")
    script = (PACKAGE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")

    assert 'self.fields["part"].widget = forms.HiddenInput()' in form_source
    assert "data-part-search" in template
    assert "findParts(query)" in script
    assert "partSearchApi" in script


def test_reference_style_defaults_are_present():
    source = (PACKAGE_ROOT / "core.py").read_text(encoding="utf-8")

    assert '"default": "Spare Parts"' in source
    assert '"default": "DI-COR Engineering"' in source
    assert '"default": "Stock"' in source
