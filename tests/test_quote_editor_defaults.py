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


def test_defaults_are_managed_from_the_main_quote_workspace():
    list_template = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_list.html"
    ).read_text(encoding="utf-8")
    editor_template = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_editor.html"
    ).read_text(encoding="utf-8")
    views = (PACKAGE_ROOT / "views.py").read_text(encoding="utf-8")

    assert "_quote_defaults.html" in list_template
    assert "_quote_defaults.html" not in editor_template
    assert "def quote_list(request, plugin):" in views
    assert 'request.POST.get("form_action") == "save_defaults"' in views


def test_new_quote_submission_is_idempotent_and_preview_opens_a_new_tab():
    editor_template = (
        PACKAGE_ROOT / "templates" / "inventree_quote_generator" / "quote_editor.html"
    ).read_text(encoding="utf-8")
    views = (PACKAGE_ROOT / "views.py").read_text(encoding="utf-8")

    assert 'name="submission_token"' in editor_template
    assert "QUOTE_SUBMISSION_SESSION_KEY" in views
    assert 'target="_blank"' in editor_template
    assert "Save and preview PDF" not in editor_template
