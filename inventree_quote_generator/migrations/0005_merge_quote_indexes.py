"""Join the historical server-generated index branch and the Sage branch.

Neither dependency may be rewritten: existing databases have already applied
both paths. This merge records their common successor without changing data.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('inventree_quote_generator', '0003_rename_inventree_q_status_1d39aa_idx_inventree_q_status_caae15_idx_and_more'),
        ('inventree_quote_generator', '0004_quote_sage_handoff'),
    ]

    operations = []
