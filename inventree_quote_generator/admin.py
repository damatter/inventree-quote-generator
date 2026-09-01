"""Admin registration for quote records."""

from django.contrib import admin

from .models import Quote, QuoteLineItem, QuoteSequence


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 0


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["quote_number", "customer_name", "issue_date", "status", "updated"]
    list_filter = ["status", "issue_date", "currency"]
    search_fields = ["quote_number", "customer_name", "subject"]
    inlines = [QuoteLineItemInline]


@admin.register(QuoteSequence)
class QuoteSequenceAdmin(admin.ModelAdmin):
    list_display = ["year", "next_number"]
