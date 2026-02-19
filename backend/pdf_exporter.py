"""
Enterprise SAR PDF Generator (Regulatory Narrative Format)
Unicode safe, multi-page, professional compliance layout
"""

from __future__ import annotations
from typing import Dict, List
import datetime as dt
from pathlib import Path
from fpdf import FPDF


# =========================================================
# CONFIGURATION
# =========================================================

SECTION_ORDER: List[str] = [
    "Subject Information",
    "Summary of Suspicious Activity",
    "Account Background",
    "Description of Suspicious Transactions",
    "Pattern Analysis",
    "Risk Indicators",
    "Investigative Findings",
    "Conclusion",
    "Supporting Evidence",
]

ORG_PLACEHOLDER = "[Organization Name]"

COMPLIANCE_DECLARATION = (
    "This Suspicious Activity Report has been prepared based on the evidence available, "
    "monitoring triggers, and investigative procedures performed as of the generation timestamp. "
    "All information is provided in good faith to support regulatory review and potential law enforcement action."
)


# =========================================================
# SAFE TEXT
# =========================================================

def _safe_text(value: object) -> str:
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


# =========================================================
# PDF CLASS WITH HEADER / FOOTER
# =========================================================

class SarPDF(FPDF):
    def __init__(self, case_id: str, org_name: str, generated_at: str, font_dir: Path):
        super().__init__()

        self.case_id = case_id or "N/A"
        self.org_name = org_name or ORG_PLACEHOLDER
        self.generated_at = generated_at

        # Margins
        self.set_auto_page_break(auto=True, margin=18)
        self.set_left_margin(16)
        self.set_right_margin(16)

        # Unicode fonts (REQUIRED)
        self.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"), uni=True)
        self.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"), uni=True)
        self.add_font("DejaVu", "I", str(font_dir / "DejaVuSans-Oblique.ttf"), uni=True)

        self.alias_nb_pages()

    # -----------------------------------------------------

    def header(self):
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 8, "SUSPICIOUS ACTIVITY REPORT", ln=1)

        self.set_font("DejaVu", "", 9)
        self.cell(0, 6, f"Case ID: {self.case_id}", ln=1)
        self.cell(0, 6, f"Generated (UTC): {self.generated_at}", ln=1)
        self.cell(0, 6, f"Organization: {self.org_name}", ln=1)

        self._divider()
        self.ln(3)

    # -----------------------------------------------------

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 5, f"CONFIDENTIAL - AML SAR    Page {self.page_no()}/{{nb}}")

    # -----------------------------------------------------

    def _divider(self):
        y = self.get_y() + 1
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, y, self.w - self.r_margin, y)


# =========================================================
# LAYOUT HELPERS
# =========================================================

def section_divider(pdf: FPDF):
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(6)


# =========================================================
# EXECUTIVE SUMMARY
# =========================================================

def render_case_summary(pdf: FPDF, narrative: Dict[str, object]):
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 8, "EXECUTIVE CASE SUMMARY", ln=1)

    pdf.set_font("DejaVu", "", 11)

    risk_level = _safe_text(narrative.get("risk_level") or "N/A").upper()
    risk_score = narrative.get("risk_score") or 0
    confidence = narrative.get("confidence_level") or 0

    pdf.multi_cell(
        0,
        6,
        f"Risk Level: {risk_level} | Risk Score: {round(risk_score,2)} | Confidence: {round(confidence,2)}"
    )

    contrib = narrative.get("contributing_factors") or {}
    if contrib:
        pdf.ln(2)
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 6, "Key Contributing Factors", ln=1)
        pdf.set_font("DejaVu", "", 10)
        for k, v in contrib.items():
            pdf.multi_cell(0, 5.5, f"- {k}: {_safe_text(v)}")

    pdf.ln(4)


# =========================================================
# RISK OVERVIEW
# =========================================================

def render_risk_overview(pdf: FPDF, narrative: Dict[str, object]):
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "RISK OVERVIEW", ln=1)

    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(
        0,
        5.5,
        f"Overall risk posture is assessed as {_safe_text(narrative.get('risk_level')).upper()} "
        f"with computed score {round(narrative.get('risk_score') or 0,2)}."
    )
    pdf.multi_cell(
        0,
        5.5,
        f"Model confidence level is {round(narrative.get('confidence_level') or 0,2)}."
    )
    pdf.ln(4)


# =========================================================
# EVIDENCE
# =========================================================

def render_evidence_summary(pdf: FPDF, narrative: Dict[str, object]):
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "SUPPORTING EVIDENCE SUMMARY", ln=1)

    pdf.set_font("DejaVu", "", 10)
    citations = narrative.get("evidence_citations") or []

    if not citations:
        pdf.multi_cell(0, 5.5, "No supporting evidence citations provided.")
    else:
        for i, cite in enumerate(citations, 1):
            pdf.multi_cell(0, 5.5, f"{i}. {_safe_text(cite)}")

    pdf.ln(4)


# =========================================================
# NARRATIVE
# =========================================================

def render_narrative_sections(pdf: FPDF, narrative: Dict[str, object]):
    sections = narrative.get("sections", {}) or {}

    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 8, "SAR NARRATIVE", ln=1)
    pdf.ln(2)

    for section in SECTION_ORDER:
        text = _safe_text(sections.get(section)).strip()
        if not text:
            continue

        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 7, section.upper(), ln=1)

        pdf.set_font("DejaVu", "", 11)
        pdf.multi_cell(0, 5.5, text)
        pdf.ln(3)


# =========================================================
# COMPLIANCE
# =========================================================

def render_compliance_declaration(pdf: FPDF):
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "COMPLIANCE DECLARATION", ln=1)

    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(0, 5.5, COMPLIANCE_DECLARATION)
    pdf.ln(3)


# =========================================================
# MAIN GENERATOR
# =========================================================

def generate_pdf(narrative: Dict[str, object]) -> bytes:
    timestamp = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    case_id = _safe_text(narrative.get("case_id"))
    font_dir = Path(__file__).resolve().parent / "fonts"

    pdf = SarPDF(case_id, ORG_PLACEHOLDER, timestamp, font_dir)

    # PAGE 1
    pdf.add_page()
    render_case_summary(pdf, narrative)
    section_divider(pdf)
    render_risk_overview(pdf, narrative)
    section_divider(pdf)
    render_evidence_summary(pdf, narrative)

    # NARRATIVE PAGE
    pdf.add_page()
    render_narrative_sections(pdf, narrative)
    render_compliance_declaration(pdf)

    raw_pdf = pdf.output(dest="S")
    pdf_bytes = raw_pdf.encode("latin-1") if isinstance(raw_pdf, str) else bytes(raw_pdf)

    if not pdf_bytes:
        raise ValueError("Empty PDF output")

    return pdf_bytes
