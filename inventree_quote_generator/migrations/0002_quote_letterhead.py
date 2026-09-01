from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventree_quote_generator", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="company_name",
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="quote",
            name="company_address",
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="quote",
            name="company_phone",
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
    ]
