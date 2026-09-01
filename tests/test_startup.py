"""Regression tests for safe plugin discovery before Django model registration."""

import ast
import importlib
import sys
from pathlib import Path
from types import ModuleType

PACKAGE_ROOT = Path(__file__).parents[1] / "inventree_quote_generator"


def top_level_imports(filename: str) -> set[str]:
    tree = ast.parse((PACKAGE_ROOT / filename).read_text(encoding="utf-8"))
    modules = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add("." * node.level + (node.module or ""))
    return modules


def test_entry_point_defers_inventree_models():
    imports = top_level_imports("core.py")
    assert "part.models" not in imports
    assert ".models" not in imports
    assert ".views" not in imports


def test_entry_point_imports_with_only_discovery_dependencies(monkeypatch):
    django_module = ModuleType("django")
    django_module.__path__ = []
    django_utils_module = ModuleType("django.utils")
    django_utils_module.__path__ = []
    translation_module = ModuleType("django.utils.translation")
    translation_module.gettext_lazy = lambda value: value

    plugin_module = ModuleType("plugin")
    mixins_module = ModuleType("plugin.mixins")

    class InvenTreePlugin:
        pass

    class AppMixin:
        pass

    class SettingsMixin:
        pass

    class UrlsMixin:
        pass

    class UserInterfaceMixin:
        pass

    plugin_module.InvenTreePlugin = InvenTreePlugin
    mixins_module.AppMixin = AppMixin
    mixins_module.SettingsMixin = SettingsMixin
    mixins_module.UrlsMixin = UrlsMixin
    mixins_module.UserInterfaceMixin = UserInterfaceMixin

    for name, module in {
        "django": django_module,
        "django.utils": django_utils_module,
        "django.utils.translation": translation_module,
        "plugin": plugin_module,
        "plugin.mixins": mixins_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    sys.modules.pop("inventree_quote_generator.core", None)
    imported = importlib.import_module("inventree_quote_generator.core")

    assert imported.QuoteGeneratorPlugin.SLUG == "quote-generator"
    assert "part.models" not in sys.modules
    assert "inventree_quote_generator.models" not in sys.modules
    assert "inventree_quote_generator.views" not in sys.modules


def test_admin_registration_is_safe_to_reload():
    source = (PACKAGE_ROOT / "admin.py").read_text(encoding="utf-8")

    assert "@admin.register" not in source
    assert "admin.site.is_registered(model)" in source
