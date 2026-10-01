"""
PDF generation for Quotation and Proforma Invoice.
Uses ReportLab to produce a professional Pacfully-branded document.
The function returns the absolute path to the saved PDF file.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.colors import HexColor

# ── Brand colours ────────────────────────────────────────────
ORANGE      = HexColor("#FF5A3A")
ORANGE_LIGHT = HexColor("#FFF1ED")
INK         = HexColor("#1A1D23")
MUTED       = HexColor("#6B7280")
LINE        = HexColor("#E5E9EE")
WHITE       = colors.white
BLACK       = colors.black

# ── Output directory ─────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(os.getenv("PDF_DIR", BASE_DIR / "data" / "pdfs")).expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _fmt_inr(value: float) -> str:
    """Format a number as Indian Rupee string: ₹ 23,030.00"""
    return f"\u20b9 {value:,.2f}"


def _safe(val):
    return str(val) if val is not None else ""


def _document_date(quotation_data: dict) -> datetime:
    value = quotation_data.get("document_date")
    if isinstance(value, datetime):
        return value
    if value:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            pass
    return datetime.utcnow()


def generate_quotation_pdf(quotation_data: dict, output_path: str | Path | None = None) -> str:
    """
    Generate a Quotation PDF.
    quotation_data keys:
      quotation_number, doc_type, customer_name, customer_address,
      job_name, order_quantity, unit_price, subtotal, gst_percent,
      gst_amount, grand_total, validity_days, notes,
      cost_lines (list of {module, total_cost, cost_per_box, weightage_pct})
    Returns: absolute path string to the generated PDF.
    """
    doc_type    = quotation_data.get("doc_type", "Quotation")
    raw_q_num   = _safe(quotation_data.get("quotation_number", "QUO-000"))
    q_num       = escape(raw_q_num)
    filename    = f"{raw_q_num.replace('/', '-')}.pdf"
    filepath    = Path(output_path) if output_path else OUTPUT_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        s = ParagraphStyle(name, **kwargs)
        return s

    title_style  = style("title",  fontName="Helvetica-Bold", fontSize=22, textColor=ORANGE)
    sub_style    = style("sub",    fontName="Helvetica",      fontSize=8,  textColor=MUTED)
    h2_style     = style("h2",     fontName="Helvetica-Bold", fontSize=13, textColor=INK)
    h3_style     = style("h3",     fontName="Helvetica-Bold", fontSize=10, textColor=INK)
    body_style   = style("body",   fontName="Helvetica",      fontSize=9,  textColor=INK)
    muted_style  = style("muted",  fontName="Helvetica",      fontSize=8,  textColor=MUTED)
    right_style  = style("right",  fontName="Helvetica",      fontSize=9,  textColor=INK,   alignment=TA_RIGHT)
    orange_style = style("orange", fontName="Helvetica-Bold", fontSize=11, textColor=ORANGE, alignment=TA_RIGHT)
    label_style  = style("label",  fontName="Helvetica",      fontSize=7,  textColor=MUTED, letterSpacing=1)

    today    = _document_date(quotation_data)
    validity = today + timedelta(days=int(quotation_data.get("validity_days", 15)))

    story = []

    # ── Header bar ───────────────────────────────────────────
    header_data = [[
        Paragraph("Pacfully", title_style),
        Table(
            [[Paragraph(doc_type.upper(), style("dtitle", fontName="Helvetica-Bold", fontSize=14, textColor=INK, alignment=TA_RIGHT))],
             [Paragraph(q_num, style("dnum", fontName="Helvetica", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))],
             [Paragraph(today.strftime("%d %b %Y"), style("ddate", fontName="Helvetica", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))]],
            colWidths=[85*mm],
            style=TableStyle([("ALIGN", (0,0), (-1,-1), "RIGHT"), ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 1)]),
        )
    ]]
    header_tbl = Table(header_data, colWidths=[95*mm, 85*mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=4*mm))

    # ── Bill To / Document Details row ───────────────────────
    customer_name = escape(_safe(quotation_data.get("customer_name", "")))
    customer_addr = escape(_safe(quotation_data.get("customer_address", "")))

    bill_content = [
        [Paragraph("BILL TO", label_style)],
        [Paragraph(customer_name, h3_style)],
        [Paragraph(customer_addr.replace("\n", "<br/>"), muted_style)],
    ]
    doc_details_content = [
        [Paragraph("DOCUMENT DETAILS", label_style)],
        [Table(
            [
                [Paragraph("Quotation No.", muted_style), Paragraph(q_num, style("qn", fontName="Helvetica-Bold", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
                [Paragraph("Date", muted_style), Paragraph(today.strftime("%d %b %Y"), style("qd", fontName="Helvetica", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
                [Paragraph("Valid Until", muted_style), Paragraph(validity.strftime("%d %b %Y"), style("qv", fontName="Helvetica", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
            ],
            colWidths=[35*mm, 45*mm],
            style=TableStyle([
                ("TOPPADDING", (0,0), (-1,-1), 2),
                ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                ("ALIGN", (1,0), (1,-1), "RIGHT"),
            ]),
        )],
    ]

    info_row = Table(
        [[Table(bill_content, colWidths=[90*mm], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)])),
          Table(doc_details_content, colWidths=[90*mm], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))]],
        colWidths=[95*mm, 85*mm],
    )
    story.append(info_row)
    story.append(Spacer(1, 4*mm))

    # ── Line items table ─────────────────────────────────────
    job_name = escape(_safe(quotation_data.get("job_name", "Packaging")))
    qty      = int(quotation_data.get("order_quantity", 0))
    unit_p   = float(quotation_data.get("unit_price", 0))
    subtotal = float(quotation_data.get("subtotal", 0))
    gst_pct  = float(quotation_data.get("gst_percent", 18))
    gst_amt  = float(quotation_data.get("gst_amount", 0))
    grand    = float(quotation_data.get("grand_total", 0))

    items_data = [
        [Paragraph("Description", style("th", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED)),
         Paragraph("Qty", style("thr", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
         Paragraph("Unit Price", style("thr2", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
         Paragraph("Total", style("thr3", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))],
        [Paragraph(job_name, body_style),
         Paragraph(f"{qty:,}", right_style),
         Paragraph(_fmt_inr(unit_p), right_style),
         Paragraph(_fmt_inr(subtotal), right_style)],
    ]
    items_tbl = Table(items_data, colWidths=[95*mm, 25*mm, 35*mm, 25*mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), LINE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, HexColor("#FAFBFC")]),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("LINEBELOW",    (0,0), (-1,0), 0.5, LINE),
        ("LINEBELOW",    (0,-1), (-1,-1), 0.5, LINE),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 3*mm))

    # ── Totals block ─────────────────────────────────────────
    totals_data = [
        [Paragraph("Subtotal", muted_style),     Paragraph(_fmt_inr(subtotal), right_style)],
        [Paragraph(f"GST ({gst_pct:.0f}%)", muted_style), Paragraph(_fmt_inr(gst_amt), right_style)],
        [Paragraph("Total Order Value", style("tot", fontName="Helvetica-Bold", fontSize=11, textColor=INK)),
         Paragraph(_fmt_inr(grand), orange_style)],
    ]
    totals_tbl = Table(totals_data, colWidths=[130*mm, 50*mm])
    totals_tbl.setStyle(TableStyle([
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LINEABOVE",    (0,2), (-1,2), 1, INK),
        ("LINEBELOW",    (0,2), (-1,2), 1, INK),
        ("ALIGN",        (1,0), (1,-1), "RIGHT"),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Cost breakdown (only shown internally — not sent to customer) ──
    # Omitted from customer-facing PDF as per spec.

    # ── Terms ────────────────────────────────────────────────
    notes_text = quotation_data.get("notes", "")
    if notes_text:
        story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3*mm))
        story.append(Paragraph("Terms & Conditions", h3_style))
        story.append(Spacer(1, 2*mm))
        for line in notes_text.split("\n"):
            if line.strip():
                story.append(Paragraph(escape(line.strip()), muted_style))
                story.append(Spacer(1, 1*mm))

    story.append(Spacer(1, 6*mm))

    # ── Footer ───────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3*mm))
    footer_data = [[
        Paragraph("Pacfully Packaging Pvt Ltd", style("fl", fontName="Helvetica-Bold", fontSize=8, textColor=INK)),
        Paragraph(
            "Internal manufacturing cost, module breakdown and margin are<br/>intentionally excluded from this document.",
            style("fr", fontName="Helvetica", fontSize=7, textColor=MUTED, alignment=TA_RIGHT)
        ),
    ]]
    footer_tbl = Table(footer_data, colWidths=[95*mm, 85*mm])
    footer_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(footer_tbl)

    doc.build(story)
    return str(filepath)


def generate_proforma_pdf(quotation_data: dict, output_path: str | Path | None = None) -> str:
    """
    Generate a Proforma Invoice PDF.
    Same as quotation but with additional bank details and proforma branding.
    """
    quotation_data = dict(quotation_data)
    quotation_data["doc_type"] = "Proforma Invoice"
    raw_q_num = _safe(quotation_data.get("quotation_number", "PI-000"))
    q_num = escape(raw_q_num)
    quotation_data["quotation_number"] = q_num

    filename = f"{raw_q_num.replace('/', '-')}.pdf"
    filepath = Path(output_path) if output_path else OUTPUT_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Reuse quotation generator with proforma doc_type
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )

    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    title_style  = style("title",  fontName="Helvetica-Bold", fontSize=22, textColor=ORANGE)
    sub_style    = style("sub",    fontName="Helvetica",      fontSize=8,  textColor=MUTED)
    h2_style     = style("h2",     fontName="Helvetica-Bold", fontSize=13, textColor=INK)
    h3_style     = style("h3",     fontName="Helvetica-Bold", fontSize=10, textColor=INK)
    body_style   = style("body",   fontName="Helvetica",      fontSize=9,  textColor=INK)
    muted_style  = style("muted",  fontName="Helvetica",      fontSize=8,  textColor=MUTED)
    right_style  = style("right",  fontName="Helvetica",      fontSize=9,  textColor=INK,   alignment=TA_RIGHT)
    orange_style = style("orange", fontName="Helvetica-Bold", fontSize=13, textColor=ORANGE, alignment=TA_RIGHT)
    label_style  = style("label",  fontName="Helvetica",      fontSize=7,  textColor=MUTED, letterSpacing=1)

    today    = _document_date(quotation_data)
    validity = today + timedelta(days=int(quotation_data.get("validity_days", 15)))

    story = []

    # Header
    header_data = [[
        Paragraph("Pacfully", title_style),
        Table(
            [[Paragraph("PROFORMA INVOICE", style("dtitle", fontName="Helvetica-Bold", fontSize=14, textColor=INK, alignment=TA_RIGHT))],
             [Paragraph(q_num, style("dnum", fontName="Helvetica", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))],
             [Paragraph(today.strftime("%d %b %Y"), style("ddate", fontName="Helvetica", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))]],
            colWidths=[85*mm],
            style=TableStyle([("ALIGN", (0,0), (-1,-1), "RIGHT"), ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 1)]),
        )
    ]]
    header_tbl = Table(header_data, colWidths=[95*mm, 85*mm])
    header_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(header_tbl)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=4*mm))

    # Bill To
    customer_name = escape(_safe(quotation_data.get("customer_name", "")))
    customer_addr = escape(_safe(quotation_data.get("customer_address", "")))

    addr_block = [
        [Paragraph("BILL TO / SHIP TO", label_style)],
        [Paragraph(customer_name, h3_style)],
        [Paragraph(customer_addr.replace("\n", "<br/>") if customer_addr else "—", muted_style)],
    ]
    doc_block = [
        [Paragraph("DOCUMENT DETAILS", label_style)],
        [Table(
            [
                [Paragraph("Proforma No.", muted_style), Paragraph(q_num, style("pi", fontName="Helvetica-Bold", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
                [Paragraph("Date", muted_style), Paragraph(today.strftime("%d %b %Y"), style("pd", fontName="Helvetica", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
                [Paragraph("Due Date", muted_style), Paragraph(validity.strftime("%d %b %Y"), style("pv", fontName="Helvetica", fontSize=9, textColor=INK, alignment=TA_RIGHT))],
            ],
            colWidths=[35*mm, 45*mm],
            style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),("ALIGN",(1,0),(1,-1),"RIGHT")]),
        )],
    ]
    info_row = Table(
        [[Table(addr_block, colWidths=[90*mm], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)])),
          Table(doc_block, colWidths=[90*mm], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))]],
        colWidths=[95*mm, 85*mm],
    )
    story.append(info_row)
    story.append(Spacer(1, 4*mm))

    job_name = escape(_safe(quotation_data.get("job_name", "Packaging")))
    qty      = int(quotation_data.get("order_quantity", 0))
    unit_p   = float(quotation_data.get("unit_price", 0))
    subtotal = float(quotation_data.get("subtotal", 0))
    gst_pct  = float(quotation_data.get("gst_percent", 18))
    gst_amt  = float(quotation_data.get("gst_amount", 0))
    grand    = float(quotation_data.get("grand_total", 0))

    items_data = [
        [Paragraph("Description", style("th", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED)),
         Paragraph("Qty", style("thr", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
         Paragraph("Unit Price", style("thr2", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
         Paragraph("Amount", style("thr3", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_RIGHT))],
        [Paragraph(job_name, body_style), Paragraph(f"{qty:,}", right_style), Paragraph(_fmt_inr(unit_p), right_style), Paragraph(_fmt_inr(subtotal), right_style)],
    ]
    items_tbl = Table(items_data, colWidths=[95*mm, 25*mm, 35*mm, 25*mm])
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LINE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,HexColor("#FAFBFC")]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("LINEBELOW",(0,0),(-1,0),0.5,LINE),("LINEBELOW",(0,-1),(-1,-1),0.5,LINE),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 3*mm))

    totals_data = [
        [Paragraph("Subtotal", muted_style), Paragraph(_fmt_inr(subtotal), right_style)],
        [Paragraph(f"GST ({gst_pct:.0f}%)", muted_style), Paragraph(_fmt_inr(gst_amt), right_style)],
        [Paragraph("Grand Total", style("tot", fontName="Helvetica-Bold", fontSize=12, textColor=INK)), Paragraph(_fmt_inr(grand), orange_style)],
    ]
    totals_tbl = Table(totals_data, colWidths=[130*mm, 50*mm])
    totals_tbl.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LINEABOVE",(0,2),(-1,2),1,INK),("LINEBELOW",(0,2),(-1,2),1,INK),
        ("ALIGN",(1,0),(1,-1),"RIGHT"),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 5*mm))

    # Bank details
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3*mm))
    story.append(Paragraph("Bank Details", h3_style))
    story.append(Spacer(1, 2*mm))
    bank = [
        ["Bank", "HDFC Bank"],
        ["Account No.", "50100123456789"],
        ["IFSC", "HDFC0001234"],
        ["Branch", "Chennai Main"],
    ]
    for row in bank:
        story.append(Table(
            [[Paragraph(row[0], muted_style), Paragraph(row[1], body_style)]],
            colWidths=[35*mm, 80*mm],
            style=TableStyle([("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]),
        ))

    story.append(Spacer(1, 4*mm))
    notes_text = quotation_data.get("notes", "")
    if notes_text:
        story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3*mm))
        story.append(Paragraph("Terms & Conditions", h3_style))
        story.append(Spacer(1, 2*mm))
        for line in notes_text.split("\n"):
            if line.strip():
                story.append(Paragraph(escape(line.strip()), muted_style))
                story.append(Spacer(1, 1*mm))

    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=3*mm))
    story.append(Paragraph("Pacfully Packaging Pvt Ltd — PACKAGING ENGINEERED", style("footer", fontName="Helvetica", fontSize=7, textColor=MUTED, alignment=TA_CENTER)))

    doc.build(story)
    return str(filepath)
