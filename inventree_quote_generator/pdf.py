"""Render polished letter-style quote PDFs matching the supplied reference."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

LOGO_BASE64 = (
    "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"
    "EhH9mYIAAAAASUVORK5CYII="
)

# The source PDF stores its logo with a separate color mask. This rendered crop preserves
# the exact black/red artwork on white instead of exposing the un-applied black mask.
DISPLAY_LOGO_BASE64 = (
    "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"
)


@dataclass(frozen=True)
class QuoteDocumentLine:
    quantity: Decimal | None = None
    unit: str = ""
    description: str = ""
    part_number: str = ""
    unit_price: Decimal | None = None
    currency: str = "CAD"
    availability: str = ""
    notes: str = ""

    @property
    def total(self) -> Decimal | None:
        if self.quantity is None or self.unit_price is None:
            return None
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class QuoteDocument:
    quote_number: str
    issue_date: date
    customer_name: str
    attention: str = ""
    subject: str = ""
    intro_text: str = ""
    manufacturer: str = ""
    item_name: str = ""
    model_name: str = ""
    availability: str = ""
    currency: str = "CAD"
    currency_terms: str = ""
    availability_terms: str = ""
    validity_terms: str = ""
    sale_terms: str = ""
    closing_text: str = ""
    tax_note: str = ""
    fob_note: str = ""
    signatory_name: str = ""
    signatory_title: str = ""
    company_name: str = "DI-COR Engineering"
    company_address: str = "33 ROSELAND DRIVE, CARRYING PLACE, ONTARIO, CANADA K0K1L0"
    company_phone: str = "PHONE: (613) 392-7302"
    show_totals: bool = False
    lines: tuple[QuoteDocumentLine, ...] = field(default_factory=tuple)


def _safe_text(value: object) -> str:
    text = str(value or "")
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\xa0", " ")
    )


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value.normalize(), "f")


def _money_text(value: Decimal | None, currency: str) -> str:
    if value is None:
        return ""
    amount = f"{value:,.2f}"
    code = (currency or "").upper()
    return f"${amount}" if code in {"CAD", "USD"} else f"{code} {amount}".strip()


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    """Wrap paragraphs by measured PDF text width."""

    lines: list[str] = []
    for paragraph in _safe_text(text).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words.pop(0)
        for word in words:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font, size) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _fit_size(text: str, font: str, preferred: float, minimum: float, width: float) -> float:
    """Shrink a single letterhead line only when the configured wording needs it."""

    size = preferred
    while size > minimum and stringWidth(_safe_text(text), font, size) > width:
        size -= 0.5
    return size


def _draw_letterhead(pdf: canvas.Canvas, document: QuoteDocument, page_number: int) -> None:
    pdf.drawImage(
        ImageReader(BytesIO(base64.b64decode(DISPLAY_LOGO_BASE64))),
        50,
        680,
        width=76,
        height=72,
        preserveAspectRatio=True,
        mask="auto",
    )
    if document.company_name:
        heading_size = _fit_size(document.company_name, "Helvetica-Bold", 18, 12, 395)
        pdf.setFont("Helvetica-Bold", heading_size)
        pdf.drawCentredString(340, 694, _safe_text(document.company_name))

    letterhead_y = 681
    if document.company_address:
        address_lines = _wrap(document.company_address, "Helvetica", 8.5, 420)
        for address_line in address_lines:
            address_size = _fit_size(address_line, "Helvetica", 8.5, 6.5, 420)
            pdf.setFont("Helvetica", address_size)
            pdf.drawCentredString(340, letterhead_y, _safe_text(address_line))
            letterhead_y -= 10
    if document.company_phone:
        phone_size = _fit_size(document.company_phone, "Helvetica", 8.5, 6.5, 420)
        pdf.setFont("Helvetica", phone_size)
        pdf.drawCentredString(340, letterhead_y, _safe_text(document.company_phone))
    if page_number > 1:
        pdf.setFont("Helvetica", 8)
        pdf.setFillGray(0.42)
        pdf.drawRightString(558, 684, f"{_safe_text(document.quote_number)} - Page {page_number}")
        pdf.setFillGray(0)


def _new_page(pdf: canvas.Canvas, document: QuoteDocument, page_number: int) -> float:
    pdf.showPage()
    _draw_letterhead(pdf, document, page_number)
    return 635


def _draw_lines(
    pdf: canvas.Canvas,
    lines: list[str],
    x: float,
    y: float,
    font: str,
    size: float,
    leading: float,
) -> float:
    pdf.setFont(font, size)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _draw_price_headers(pdf: canvas.Canvas, y: float) -> float:
    """Draw compact column labels for quote pricing."""

    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillGray(0.3)
    pdf.drawString(54, y, "Qty. / description / part")
    pdf.drawRightString(451, y, "Price ea.")
    pdf.drawRightString(558, y, "Extended price")
    pdf.setStrokeGray(0.78)
    pdf.line(54, y - 4, 558, y - 4)
    pdf.setStrokeGray(0)
    pdf.setFillGray(0)
    return y - 17


def quote_document_from_model(quote, plugin) -> QuoteDocument:
    """Build a renderer-friendly snapshot without importing models at module load time."""

    def letterhead_value(field_name: str, setting_key: str, fallback: str = "") -> str:
        value = getattr(quote, field_name, None)
        if value is None:
            value = plugin.get_setting(setting_key)
        return fallback if value is None else value

    settings = {
        "company_name": letterhead_value(
            "company_name", "COMPANY_NAME", "DI-COR Engineering"
        ),
        "company_address": letterhead_value("company_address", "COMPANY_ADDRESS"),
        "company_phone": letterhead_value("company_phone", "COMPANY_PHONE"),
    }
    lines = tuple(
        QuoteDocumentLine(
            quantity=item.quantity,
            unit=item.unit,
            description=item.description,
            part_number=item.part_number,
            unit_price=item.unit_price,
            currency=item.currency or quote.currency,
            availability=item.availability,
            notes=item.notes,
        )
        for item in quote.line_items.all()
    )
    return QuoteDocument(
        quote_number=quote.quote_number,
        issue_date=quote.issue_date,
        customer_name=quote.customer_name or quote.customer.name,
        attention=quote.attention,
        subject=quote.subject,
        intro_text=quote.intro_text,
        manufacturer=quote.manufacturer,
        item_name=quote.item_name,
        model_name=quote.model_name,
        availability=quote.availability,
        currency=quote.currency,
        currency_terms=quote.currency_terms,
        availability_terms=quote.availability_terms,
        validity_terms=quote.validity_terms,
        sale_terms=quote.sale_terms,
        closing_text=quote.closing_text,
        tax_note=quote.tax_note,
        fob_note=quote.fob_note,
        signatory_name=quote.signatory_name,
        signatory_title=quote.signatory_title,
        show_totals=quote.show_totals,
        lines=lines,
        **settings,
    )


def render_quote_pdf(document: QuoteDocument) -> bytes:
    """Render a quote to PDF bytes using the supplied DI-COR letter layout."""

    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=letter, pageCompression=1)
    pdf.setTitle(f"Quote {document.quote_number}")
    pdf.setAuthor(document.company_name)

    page_number = 1
    _draw_letterhead(pdf, document, page_number)
    y = 634

    pdf.setFont("Times-Roman", 13)
    date_text = document.issue_date.strftime("%B %d, %Y").replace(" 0", " ")
    pdf.drawString(54, y, date_text)
    y -= 40

    if document.customer_name:
        customer_lines = _wrap(document.customer_name.upper(), "Times-Roman", 13, 504)
        y = _draw_lines(pdf, customer_lines, 54, y, "Times-Roman", 13, 15)
        y -= 5
    if document.attention:
        attention_lines = _wrap(
            f"ATTENTION: {document.attention}", "Times-Roman", 11, 504
        )
        y = _draw_lines(pdf, attention_lines, 54, y, "Times-Roman", 11, 13)
        y -= 7
    y -= 8

    if document.subject:
        subject_lines = _wrap(f"SUBJECT: {document.subject}", "Times-Roman", 13, 504)
        y = _draw_lines(pdf, subject_lines, 54, y, "Times-Roman", 13, 15)
        y -= 13

    if document.intro_text:
        intro = _wrap(document.intro_text, "Times-Roman", 11.5, 504)
        y = _draw_lines(pdf, intro, 54, y, "Times-Roman", 11.5, 14)
        y -= 12

    for label, value in (
        ("Manufacturer:", document.manufacturer),
        ("Item Name:", document.item_name),
        ("Model:", document.model_name),
    ):
        if not value:
            continue
        value_lines = _wrap(value, "Times-Roman", 11.5, 426)
        pdf.setFont("Times-Bold", 11.5)
        pdf.drawString(54, y, label)
        y = _draw_lines(pdf, value_lines, 132, y, "Times-Roman", 11.5, 14)
    y -= 18

    if document.lines:
        y = _draw_price_headers(pdf, y)

    for item in document.lines:
        quantity = _decimal_text(item.quantity)
        quantity_unit = f"{quantity}{_safe_text(item.unit)}" if quantity else _safe_text(item.unit)
        segments = [value for value in (quantity_unit, item.description, item.part_number) if value]
        left_text = " - ".join(_safe_text(value) for value in segments)
        wrapped = _wrap(left_text, "Times-Roman", 11.5, 292) if left_text else [""]
        note_lines = _wrap(item.notes, "Times-Italic", 9.5, 430) if item.notes else []
        needed = max(
            22,
            len(wrapped) * 14
            + (14 if item.availability else 0)
            + len(note_lines) * 12,
        )
        if y - needed < 205:
            page_number += 1
            y = _new_page(pdf, document, page_number)
            y = _draw_price_headers(pdf, y)

        y = _draw_lines(pdf, wrapped, 54, y, "Times-Roman", 11.5, 14)
        price = _money_text(item.unit_price, item.currency or document.currency)
        if price:
            pdf.setFont("Times-Roman", 11.5)
            pdf.drawRightString(451, y + 14, price)
        extended_price = _money_text(item.total, item.currency or document.currency)
        if extended_price:
            pdf.setFont("Times-Roman", 11.5)
            pdf.drawRightString(558, y + 14, extended_price)
        if item.availability:
            pdf.setFont("Times-Italic", 9.5)
            pdf.setFillGray(0.35)
            pdf.drawString(72, y, _safe_text(item.availability))
            pdf.setFillGray(0)
            y -= 13
        if note_lines:
            pdf.setFillGray(0.35)
            y = _draw_lines(pdf, note_lines, 72, y, "Times-Italic", 9.5, 12)
            pdf.setFillGray(0)
        y -= 10

    if document.show_totals:
        priced_lines = [item for item in document.lines if item.total is not None]
        currencies = {(item.currency or document.currency).upper() for item in priced_lines}
        subtotal = sum((item.total for item in priced_lines), Decimal(0))
        if priced_lines and currencies == {document.currency.upper()}:
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawRightString(505, y, f"Subtotal: {_money_text(subtotal, document.currency)}")
            y -= 24

    if document.availability:
        availability_lines = _wrap(document.availability, "Times-Roman", 11.5, 504)
        y = _draw_lines(pdf, availability_lines, 54, y, "Times-Roman", 11.5, 14)
        y -= 12

    terms = []
    if document.currency_terms:
        terms.append(document.currency_terms)
    if document.availability_terms:
        terms.append(f"Availability: {document.availability_terms}")
    if document.validity_terms:
        terms.append(document.validity_terms)
    if document.sale_terms:
        terms.append(document.sale_terms)
    if terms:
        term_lines = [line for term in terms for line in _wrap(term, "Helvetica", 10.5, 385)]
        needed = len(term_lines) * 12.5 + 22
        if y - needed < 175:
            page_number += 1
            y = _new_page(pdf, document, page_number)
        pdf.setFont("Helvetica-Bold", 10.5)
        pdf.drawString(54, y, "Terms:")
        y = _draw_lines(pdf, term_lines, 123, y, "Helvetica", 10.5, 12.5)
        y -= 14

    if document.closing_text:
        closing = _wrap(document.closing_text, "Helvetica", 10.5, 504)
        if y - len(closing) * 12.5 < 120:
            page_number += 1
            y = _new_page(pdf, document, page_number)
        y = _draw_lines(pdf, closing, 54, y, "Helvetica", 10.5, 12.5)
        y -= 24

    final_lines = [
        line
        for value in (document.tax_note, document.fob_note)
        if value
        for line in _wrap(value, "Times-Roman", 11.5, 504)
    ]
    required = len(final_lines) * 14 + (54 if document.signatory_name else 0)
    if y - required < 56:
        page_number += 1
        y = _new_page(pdf, document, page_number)
    if final_lines:
        y = _draw_lines(
            pdf,
            [_safe_text(value) for value in final_lines],
            54,
            y,
            "Times-Roman",
            11.5,
            14,
        )
        y -= 14
    if document.signatory_name:
        pdf.setFont("Times-Roman", 11.5)
        pdf.drawString(54, y, "Regards,")
        y -= 27
        pdf.drawString(54, y, _safe_text(document.signatory_name).upper())
        if document.signatory_title:
            y -= 14
            pdf.setFont("Times-Roman", 10.5)
            pdf.drawString(54, y, _safe_text(document.signatory_title))

    pdf.save()
    return stream.getvalue()


def quote_pdf_filename(quote_number: str, customer_name: str, subject: str = "") -> str:
    """Return a stable filesystem-safe download name."""

    stem = " ".join(value for value in (quote_number, customer_name, subject) if value)
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "", stem).strip()
    stem = re.sub(r"[ _]+", "_", stem)
    return f"{stem or 'quote'}.pdf"
