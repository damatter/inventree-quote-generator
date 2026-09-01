"""Persistent quote records and line-item snapshots."""

from datetime import date

from company.models import Company
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from part.models import Part


class QuoteSequence(models.Model):
    """Concurrency-safe yearly quote number sequence."""

    year = models.PositiveIntegerField(unique=True)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("Quote sequence")
        verbose_name_plural = _("Quote sequences")

    def __str__(self):
        return f"{self.year}: next {self.next_number}"


def next_quote_number(issue_date: date | None = None) -> str:
    """Reserve and return the next quote number for a calendar year."""

    year = (issue_date or timezone.localdate()).year
    with transaction.atomic():
        sequence, _ = QuoteSequence.objects.select_for_update().get_or_create(year=year)
        number = sequence.next_number
        sequence.next_number = number + 1
        sequence.save(update_fields=["next_number"])
    return f"QT-{year}-{number:04d}"


class Quote(models.Model):
    """A customer quote whose presentation fields are editable snapshots."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        READY = "ready", _("Ready")
        SENT = "sent", _("Sent")
        ACCEPTED = "accepted", _("Accepted")
        DECLINED = "declined", _("Declined")
        EXPIRED = "expired", _("Expired")

    quote_number = models.CharField(max_length=32, unique=True, blank=True)
    customer = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="generated_quotes",
        limit_choices_to={"is_customer": True},
    )
    customer_name = models.CharField(max_length=255, blank=True, default="")
    attention = models.CharField(max_length=255, blank=True, default="")
    issue_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="CAD")

    subject = models.CharField(max_length=255, blank=True, default="")
    intro_text = models.TextField(blank=True, default="")
    manufacturer = models.CharField(max_length=255, blank=True, default="")
    item_name = models.CharField(max_length=255, blank=True, default="")
    model_name = models.CharField(max_length=255, blank=True, default="")
    availability = models.CharField(max_length=255, blank=True, default="")

    currency_terms = models.CharField(max_length=255, blank=True, default="")
    availability_terms = models.CharField(max_length=500, blank=True, default="")
    validity_terms = models.CharField(max_length=255, blank=True, default="")
    sale_terms = models.CharField(max_length=255, blank=True, default="")
    closing_text = models.TextField(blank=True, default="")
    tax_note = models.CharField(max_length=255, blank=True, default="")
    fob_note = models.CharField(max_length=255, blank=True, default="")
    signatory_name = models.CharField(max_length=255, blank=True, default="")
    signatory_title = models.CharField(max_length=255, blank=True, default="")
    show_totals = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="quotes_created",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="quotes_updated",
        null=True,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    generation_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-issue_date", "-pk"]
        indexes = [
            models.Index(fields=["status", "-issue_date"]),
            models.Index(fields=["customer", "-issue_date"]),
        ]

    def __str__(self):
        return f"{self.quote_number or 'New quote'} - {self.customer_name or self.customer}"

    def save(self, *args, **kwargs):
        if not self.customer_name and self.customer_id:
            self.customer_name = self.customer.name
        if not self.quote_number:
            self.quote_number = next_quote_number(self.issue_date)
        self.currency = (self.currency or "CAD").upper()
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        """Return the sum of priced line items, excluding intentionally blank prices."""

        total = None
        for line in self.line_items.all():
            if line.quantity is None or line.unit_price is None:
                continue
            amount = line.quantity * line.unit_price
            total = amount if total is None else total + amount
        return total


class QuoteLineItem(models.Model):
    """A flexible line item with a price snapshot from customer pricing or manual entry."""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="line_items")
    part = models.ForeignKey(
        Part,
        on_delete=models.SET_NULL,
        related_name="quote_line_items",
        null=True,
        blank=True,
    )
    sort_order = models.PositiveIntegerField(default=0)
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=5,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField(max_length=32, blank=True, default="pcs.")
    description = models.CharField(max_length=500, blank=True, default="")
    part_number = models.CharField(max_length=100, blank=True, default="")
    unit_price = models.DecimalField(
        max_digits=19,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(max_length=3, blank=True, default="")
    manual_price = models.BooleanField(default=False)
    price_source = models.CharField(max_length=255, blank=True, default="")
    source_price_break_id = models.PositiveIntegerField(null=True, blank=True)
    availability = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return self.description or self.part_number or f"Line {self.pk}"

    @property
    def line_total(self):
        if self.quantity is None or self.unit_price is None:
            return None
        return self.quantity * self.unit_price
