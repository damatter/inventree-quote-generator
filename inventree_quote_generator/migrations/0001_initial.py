"""Create quote, line-item, and quote-sequence tables."""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("company", "0079_auto_20260212_1054"),
        ("part", "0147_remove_part_default_supplier"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuoteSequence",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField(unique=True)),
                ("next_number", models.PositiveIntegerField(default=1)),
            ],
            options={"verbose_name": "Quote sequence", "verbose_name_plural": "Quote sequences"},
        ),
        migrations.CreateModel(
            name="Quote",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote_number", models.CharField(blank=True, max_length=32, unique=True)),
                ("customer_name", models.CharField(blank=True, default="", max_length=255)),
                ("attention", models.CharField(blank=True, default="", max_length=255)),
                ("issue_date", models.DateField(default=django.utils.timezone.localdate)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready"), ("sent", "Sent"), ("accepted", "Accepted"), ("declined", "Declined"), ("expired", "Expired")], default="draft", max_length=16)),
                ("currency", models.CharField(default="CAD", max_length=3)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                ("intro_text", models.TextField(blank=True, default="")),
                ("manufacturer", models.CharField(blank=True, default="", max_length=255)),
                ("item_name", models.CharField(blank=True, default="", max_length=255)),
                ("model_name", models.CharField(blank=True, default="", max_length=255)),
                ("availability", models.CharField(blank=True, default="", max_length=255)),
                ("currency_terms", models.CharField(blank=True, default="", max_length=255)),
                ("availability_terms", models.CharField(blank=True, default="", max_length=500)),
                ("validity_terms", models.CharField(blank=True, default="", max_length=255)),
                ("sale_terms", models.CharField(blank=True, default="", max_length=255)),
                ("closing_text", models.TextField(blank=True, default="")),
                ("tax_note", models.CharField(blank=True, default="", max_length=255)),
                ("fob_note", models.CharField(blank=True, default="", max_length=255)),
                ("signatory_name", models.CharField(blank=True, default="", max_length=255)),
                ("signatory_title", models.CharField(blank=True, default="", max_length=255)),
                ("show_totals", models.BooleanField(default=False)),
                ("internal_notes", models.TextField(blank=True, default="")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("last_generated_at", models.DateTimeField(blank=True, null=True)),
                ("generation_count", models.PositiveIntegerField(default=0)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quotes_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(limit_choices_to={"is_customer": True}, on_delete=django.db.models.deletion.PROTECT, related_name="generated_quotes", to="company.company")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quotes_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-issue_date", "-pk"]},
        ),
        migrations.CreateModel(
            name="QuoteLineItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("quantity", models.DecimalField(blank=True, decimal_places=5, max_digits=15, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ("unit", models.CharField(blank=True, default="pcs.", max_length=32)),
                ("description", models.CharField(blank=True, default="", max_length=500)),
                ("part_number", models.CharField(blank=True, default="", max_length=100)),
                ("unit_price", models.DecimalField(blank=True, decimal_places=6, max_digits=19, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ("currency", models.CharField(blank=True, default="", max_length=3)),
                ("manual_price", models.BooleanField(default=False)),
                ("price_source", models.CharField(blank=True, default="", max_length=255)),
                ("source_price_break_id", models.PositiveIntegerField(blank=True, null=True)),
                ("availability", models.CharField(blank=True, default="", max_length=255)),
                ("notes", models.TextField(blank=True, default="")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("part", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quote_line_items", to="part.part")),
                ("quote", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="line_items", to="inventree_quote_generator.quote")),
            ],
            options={"ordering": ["sort_order", "pk"]},
        ),
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["status", "-issue_date"], name="inventree_q_status_1d39aa_idx"),
        ),
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["customer", "-issue_date"], name="inventree_q_custome_77443f_idx"),
        ),
    ]
