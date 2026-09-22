"""Admin registration for quote records."""

from django.contrib import admin

from .models import Quote, QuoteLineItem, QuoteSequence


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 0


class QuoteAdmin(admin.ModelAdmin):
    list_display = [
        "quote_number",
        "customer_name",
        "issue_date",
        "status",
        "sales_order_reference",
        "updated",
    ]
    list_filter = ["status", "issue_date", "currency"]
    search_fields = ["quote_number", "customer_name", "subject"]
    inlines = [QuoteLineItemInline]


class QuoteSequenceAdmin(admin.ModelAdmin):
    list_display = ["year", "next_number"]


# InvenTree reloads plugin admin modules while refreshing AppMixin plugins.
# Register only missing models so repeated imports remain safe.
for model, model_admin in (
    (Quote, QuoteAdmin),
    (QuoteSequence, QuoteSequenceAdmin),
):
    if not admin.site.is_registered(model):
        admin.site.register(model, model_admin)
