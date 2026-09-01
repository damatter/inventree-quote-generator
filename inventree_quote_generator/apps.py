"""Django application configuration for quote generation."""

from django.apps import AppConfig


class QuoteGeneratorConfig(AppConfig):
    """Register the plugin-owned quote models."""

    default_auto_field = "django.db.models.AutoField"
    name = "inventree_quote_generator"
    verbose_name = "Quote Generator"
