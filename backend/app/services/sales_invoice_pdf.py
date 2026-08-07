"""Backend-authoritative PDF generation for sales invoices using ReportLab.

Runs on Azure Functions (pure Python, no system dependencies). The PDF is
generated from the persisted invoice document (snapshots + backend-calculated
lines); it never trusts frontend-provided totals.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.sales_invoice_calculation import format_nok

PRIMARY = colors.HexColor("#166534")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#e5e7eb")


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = {"fontName": "Helvetica", "fontSize": 9, "leading": 12, "textColor": colors.black}
    base.update(kwargs)
    return ParagraphStyle(name, **base)


def _format_date(value: Any) -> str:
    text = str(value or "")
    if len(text) == 10 and text[4:5] == "-":
        return f"{text[8:10]}.{text[5:7]}.{text[0:4]}"
    return text


def _address_block(snapshot: dict) -> str:
    lines = [snapshot.get("name") or ""]
    address = snapshot.get("address") or ""
    if address:
        lines.append(address)
    postal = snapshot.get("postal_code") or ""
    city = snapshot.get("city") or ""
    if postal or city:
        lines.append(f"{postal} {city}".strip())
    return "<br/>".join(line for line in lines if line)


def build_invoice_pdf(invoice: dict, *, draft: bool = False) -> bytes:
    """Render a sales invoice document to PDF bytes.

    For drafts, the document is watermarked/labelled UTKAST and has no
    permanent invoice number.
    """
    seller = invoice.get("seller_snapshot") or {}
    customer = invoice.get("customer_snapshot") or {}
    payment = invoice.get("payment_account_snapshot") or {}
    lines = invoice.get("lines") or []

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Fakturautkast" if draft else f"Faktura {invoice.get('invoice_number') or ''}",
    )

    title_style = _style("Title", fontSize=20, leading=24, fontName="Helvetica-Bold", textColor=PRIMARY)
    heading_style = _style("Heading", fontSize=8, fontName="Helvetica-Bold", textColor=MUTED)
    body_style = _style("Body", fontSize=9)
    small_style = _style("Small", fontSize=8, textColor=MUTED)
    right_style = _style("Right", fontSize=9, alignment=2)
    total_style = _style("Total", fontSize=11, fontName="Helvetica-Bold")

    story: list = []

    header_label = "UTKAST" if draft else "FAKTURA"
    header = Table(
        [
            [
                Paragraph(seller.get("name") or "", _style("SellerName", fontSize=13, fontName="Helvetica-Bold")),
                Paragraph(header_label, title_style),
            ]
        ],
        colWidths=[110 * mm, 60 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 4 * mm))

    # Seller / customer / meta columns
    invoice_number = invoice.get("invoice_number") or ("UTKAST" if draft else "—")
    meta_rows = [
        [
            Paragraph("SELGER", heading_style),
            Paragraph("KUNDE", heading_style),
            Paragraph("FAKTURANUMMER", heading_style),
        ],
        [
            Paragraph(_address_block(seller), body_style),
            Paragraph(_address_block(customer), body_style),
            Paragraph(str(invoice_number), body_style),
        ],
        [
            Paragraph(
                (f"Org.nr.: {seller.get('org_number')}" if seller.get("org_number") else "") + "<br/>"
                + (f"MVA-nr.: {seller.get('vat_number')}" if seller.get("vat_number") else ""),
                small_style,
            ),
            Paragraph(
                f"Org.nr.: {customer.get('org_number')}" if customer.get("org_number") else "",
                small_style,
            ),
            Paragraph(
                f"Fakturadato: {_format_date(invoice.get('invoice_date'))}<br/>"
                f"Forfallsdato: {_format_date(invoice.get('due_date'))}",
                body_style,
            ),
        ],
    ]
    meta = Table(meta_rows, colWidths=[62 * mm, 62 * mm, 46 * mm])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 6 * mm))

    if invoice.get("reference"):
        story.append(Paragraph(f"Referanse: {invoice['reference']}", body_style))
        story.append(Spacer(1, 2 * mm))

    # Line items
    table_rows = [
        [
            Paragraph("Beskrivelse", heading_style),
            Paragraph("Antall", heading_style),
            Paragraph("Enhet", heading_style),
            Paragraph("Pris eks. MVA", heading_style),
            Paragraph("MVA", heading_style),
            Paragraph("Sum", heading_style),
        ]
    ]
    for line in lines:
        table_rows.append(
            [
                Paragraph(str(line.get("description") or ""), body_style),
                Paragraph(str(line.get("quantity") or ""), right_style),
                Paragraph(str(line.get("unit") or ""), body_style),
                Paragraph(format_nok(int(line.get("unit_price_ex_vat_ore") or 0)), right_style),
                Paragraph(f"{line.get('vat_rate', 0)} %", right_style),
                Paragraph(format_nok(int(line.get("line_total_ore") or 0)), right_style),
            ]
        )

    totals = [
        ["Sum eks. MVA", format_nok(int(invoice.get("subtotal_ore") or 0))],
        ["MVA", format_nok(int(invoice.get("vat_total_ore") or 0))],
        ["Totalt", format_nok(int(invoice.get("total_ore") or 0))],
    ]

    lines_table = Table(
        table_rows + [[Spacer(1, 3 * mm)] * 6] + [[Paragraph(label, total_style if label == "Totalt" else body_style), "", "", "", "", Paragraph(amount, total_style if label == "Totalt" else body_style)] for label, amount in totals],
        colWidths=[62 * mm, 18 * mm, 18 * mm, 28 * mm, 16 * mm, 28 * mm],
    )
    lines_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                ("ALIGN", (5, 0), (5, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, PRIMARY),
                ("LINEBELOW", (0, len(table_rows) - 1), (-1, len(table_rows) - 1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(lines_table)
    story.append(Spacer(1, 8 * mm))

    # Payment information
    account_number = payment.get("account_number") or ""
    payment_lines = ["BETALING", f"Kontonummer: {account_number}" if account_number else "Kontonummer: —", f"Forfallsdato: {_format_date(invoice.get('due_date'))}", f"Beløp: {format_nok(int(invoice.get('total_ore') or 0))} NOK"]
    if invoice.get("invoice_number"):
        payment_lines.append(f"KID/referanse: Faktura {invoice['invoice_number']}")
    story.append(Paragraph("<br/>".join(payment_lines), body_style))

    if invoice.get("message"):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"Melding: {invoice['message']}", small_style))

    if draft:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Dette er et utkast og ikke en gyldig faktura.", small_style))

    document.build(story)
    return buffer.getvalue()