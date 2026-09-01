"""PDF generation regression tests for template content and pagination."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

from inventree_quote_generator.pdf import (
    QuoteDocument,
    QuoteDocumentLine,
    quote_pdf_filename,
    render_quote_pdf,
)


def sample_document(lines=None):
    return QuoteDocument(
        quote_number="QT-2026-0001",
        issue_date=date(2026, 4, 22),
        customer_name="Redpath Sugar",
        subject="Burt 704 Spare Parts",
        intro_text=(
            "Regarding your recent request, we are pleased to offer the following for "
            "your consideration:"
        ),
        manufacturer="DiCor Engineering",
        item_name="Upper Carrier Parts",
        model_name="Burt 704",
        availability="Stock",
        currency_terms="All prices in CDN. Dollars.",
        availability_terms="Stock from Receipt of Firm Purchase Order.",
        validity_terms="Estimate Valid For 30 Days.",
        sale_terms="Please see Terms of Sale.",
        closing_text="Thank you for allowing DI COR ENGINEERING, Inc. to be of service to you.",
        tax_note="Taxes extra. Prices in CDN funds.",
        fob_note="F.O.B. Redpath Plant, Belleville, Ontario",
        signatory_name="Brad Dick",
        lines=tuple(
            lines
            or [
                QuoteDocumentLine(
                    quantity=Decimal("13"),
                    unit="pcs.",
                    description="Section - Guide Rod",
                    part_number="W10372DC",
                    unit_price=Decimal("168.83"),
                    currency="CAD",
                )
            ]
        ),
    )


def test_reference_quote_content_is_rendered():
    payload = render_quote_pdf(sample_document())
    reader = PdfReader(BytesIO(payload))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert payload.startswith(b"%PDF")
    assert len(reader.pages) == 1
    assert "REDPATH SUGAR" in text
    assert "Burt 704 Spare Parts" in text
    assert "W10372DC" in text
    assert "Price ea." in text
    assert "Extended price" in text
    assert "$168.83" in text
    assert "$2,194.79" in text


def test_many_lines_continue_to_additional_pages():
    lines = [
        QuoteDocumentLine(
            quantity=Decimal(index + 1),
            unit="pcs.",
            description=f"Replacement component number {index + 1} with a longer description",
            part_number=f"PART-{index + 1:03d}",
            unit_price=Decimal("15.25"),
            currency="CAD",
        )
        for index in range(30)
    ]
    reader = PdfReader(BytesIO(render_quote_pdf(sample_document(lines))))

    assert len(reader.pages) >= 2


def test_download_filename_is_safe_and_stable():
    assert quote_pdf_filename("QT-2026-0001", "Redpath Sugar", "Burt / Parts") == (
        "QT-2026-0001_Redpath_Sugar_Burt_Parts.pdf"
    )
