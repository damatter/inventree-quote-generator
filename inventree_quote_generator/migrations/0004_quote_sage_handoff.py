"""Add direct quote-to-Sage handoff fields."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventree_quote_generator", "0003_quote_sales_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="sage_customer_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_transaction_type",
            field=models.CharField(
                choices=[("Sales Invoice", "Sales Invoice"), ("Sales Order", "Sales Order")],
                default="Sales Invoice",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_reference",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="quote",
            name="invoice_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quote",
            name="ship_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_revenue_account",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_tax_code",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_export_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_last_exported_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quote",
            name="sage_last_exported_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
