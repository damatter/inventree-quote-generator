"""Django forms for the interactive quote editor."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from company.models import Company
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone
from part.models import Part

from .models import Quote, QuoteLineItem
from .pricing import resolve_customer_price


class QuoteForm(forms.ModelForm):
    """Quote header, template wording, status, and output options."""

    class Meta:
        model = Quote
        fields = [
            "customer",
            "attention",
            "issue_date",
            "valid_until",
            "status",
            "currency",
            "subject",
            "intro_text",
            "manufacturer",
            "item_name",
            "model_name",
            "availability",
            "currency_terms",
            "availability_terms",
            "validity_terms",
            "sale_terms",
            "closing_text",
            "tax_note",
            "fob_note",
            "signatory_name",
            "signatory_title",
            "show_totals",
            "internal_notes",
        ]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "intro_text": forms.Textarea(attrs={"rows": 2}),
            "closing_text": forms.Textarea(attrs={"rows": 4}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, plugin=None, initial_part=None, **kwargs):
        super().__init__(*args, **kwargs)
        customers = Company.objects.filter(is_customer=True).filter(Q(active=True))
        if self.instance.customer_id:
            customers = Company.objects.filter(is_customer=True).filter(
                Q(active=True) | Q(pk=self.instance.customer_id)
            )
        self.fields["customer"].queryset = customers.order_by("name")
        self.fields["customer"].required = True
        self.fields["currency"].widget.attrs.update({"maxlength": 3, "data-uppercase": "true"})
        self.fields["currency"].help_text = "Three-letter currency code, such as CAD or USD."
        self.fields["internal_notes"].help_text = "Private notes; never shown on the PDF."
        self.fields["show_totals"].help_text = (
            "Show a subtotal only when every priced line uses the quote currency."
        )

        for name, field in self.fields.items():
            field.required = name in {"customer", "issue_date"}

        if not self.is_bound and not self.instance.pk and plugin is not None:
            valid_days = int(plugin.get_setting("DEFAULT_VALID_DAYS") or 30)
            issued = timezone.localdate()
            defaults = {
                "issue_date": issued,
                "valid_until": issued + timedelta(days=valid_days),
                "currency": plugin.get_setting("DEFAULT_CURRENCY") or "CAD",
                "intro_text": plugin.get_setting("INTRO_TEXT") or "",
                "currency_terms": plugin.get_setting("CURRENCY_TERMS") or "",
                "availability_terms": plugin.get_setting("AVAILABILITY_TERMS") or "",
                "validity_terms": plugin.get_setting("VALIDITY_TERMS") or "",
                "sale_terms": plugin.get_setting("SALE_TERMS") or "",
                "closing_text": plugin.get_setting("CLOSING_TEXT") or "",
                "tax_note": plugin.get_setting("TAX_NOTE") or "",
                "fob_note": plugin.get_setting("FOB_NOTE") or "",
                "signatory_name": plugin.get_setting("SIGNATORY_NAME") or "",
                "signatory_title": plugin.get_setting("SIGNATORY_TITLE") or "",
            }
            if initial_part is not None:
                defaults.update(
                    {
                        "subject": initial_part.description or initial_part.name,
                        "item_name": initial_part.name,
                    }
                )
            for name, value in defaults.items():
                self.fields[name].initial = value

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or "CAD").upper()

    def clean(self):
        cleaned = super().clean()
        issued = cleaned.get("issue_date")
        valid_until = cleaned.get("valid_until")
        if issued and valid_until and valid_until < issued:
            self.add_error("valid_until", "Valid-until date cannot be before the issue date.")
        return cleaned


class QuoteLineItemForm(forms.ModelForm):
    """Line editor which can resolve or manually snapshot a unit price."""

    PRICE_MODES = (("auto", "Customer pricing"), ("manual", "Manual price"))
    price_mode = forms.ChoiceField(choices=PRICE_MODES, required=False, initial="auto")

    class Meta:
        model = QuoteLineItem
        fields = [
            "part",
            "quantity",
            "unit",
            "description",
            "part_number",
            "price_mode",
            "unit_price",
            "currency",
            "availability",
            "notes",
        ]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 0, "step": "any"}),
            "unit_price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, customer=None, quote_currency="CAD", **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        self.quote_currency = (quote_currency or "CAD").upper()
        self.fields["part"].queryset = Part.objects.filter(active=True).order_by("name", "IPN")
        self.fields["part"].required = False
        self.fields["part"].empty_label = "Custom line item / no InvenTree part"
        for field in self.fields.values():
            field.required = False
        if self.instance.pk:
            self.fields["price_mode"].initial = (
                "manual" if self.instance.manual_price else "auto"
            )
        self.fields["currency"].widget.attrs.update({"maxlength": 3, "data-uppercase": "true"})

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or self.quote_currency).upper()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned

        part = cleaned.get("part")
        quantity = cleaned.get("quantity")
        price_mode = cleaned.get("price_mode") or "auto"

        if part and not cleaned.get("description"):
            cleaned["description"] = part.name
            self.instance.description = part.name
        if part and not cleaned.get("part_number"):
            cleaned["part_number"] = part.IPN
            self.instance.part_number = part.IPN

        if price_mode == "auto" and part and self.customer and quantity is not None:
            result = resolve_customer_price(self.customer.pk, part.pk, Decimal(quantity))
            if result.found:
                cleaned["unit_price"] = result.unit_price
                cleaned["currency"] = result.currency
                self.instance.unit_price = result.unit_price
                self.instance.currency = result.currency
                self.instance.manual_price = False
                self.instance.price_source = result.source
                self.instance.source_price_break_id = result.price_break_id
                return cleaned

            self.instance.manual_price = True
            self.instance.price_source = "Manual price - customer price not found"
            self.instance.source_price_break_id = None
            cleaned["price_mode"] = "manual"
        else:
            self.instance.manual_price = True
            self.instance.price_source = "Manual price"
            self.instance.source_price_break_id = None

        self.instance.currency = cleaned.get("currency") or self.quote_currency
        return cleaned


class BaseQuoteLineItemFormSet(BaseInlineFormSet):
    """Require at least one meaningful line while allowing every individual field to be blank."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        meaningful = False
        for form in self.forms:
            data = getattr(form, "cleaned_data", {})
            if data.get("DELETE"):
                continue
            if data.get("part") or data.get("description") or data.get("part_number"):
                meaningful = True
                break
        if not meaningful:
            raise ValidationError("Add at least one part or custom line-item description.")


QuoteLineItemFormSet = inlineformset_factory(
    Quote,
    QuoteLineItem,
    form=QuoteLineItemForm,
    formset=BaseQuoteLineItemFormSet,
    extra=1,
    can_delete=True,
)
