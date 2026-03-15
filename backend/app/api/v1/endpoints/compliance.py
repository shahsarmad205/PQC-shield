"""Compliance API: PDF report of NIST-standardized algorithms."""
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.security import get_current_user
from app.models.cbom import User

router = APIRouter()

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Rows: Algorithm, FIPS standard, Security level, Key size (pub), Key size (sec), Signature/ciphertext size
COMPLIANCE_ROWS = [
    ["Algorithm", "FIPS standard", "Security level", "Key size (pub)", "Key size (sec)", "Sig/CT size", "Quantum-safe"],
    ["ML-KEM-512", "FIPS 203", "1", "800 B", "1,632 B", "768 B (ciphertext)", "Yes"],
    ["ML-KEM-768", "FIPS 203", "3", "1,184 B", "2,400 B", "1,088 B (ciphertext)", "Yes"],
    ["ML-KEM-1024", "FIPS 203", "5", "1,568 B", "3,168 B", "1,568 B (ciphertext)", "Yes"],
    ["ML-DSA-44", "FIPS 204", "1", "1,312 B", "2,528 B", "2,420 B (signature)", "Yes"],
    ["ML-DSA-65", "FIPS 204", "3", "1,952 B", "4,032 B", "3,309 B (signature)", "Yes"],
    ["ML-DSA-87", "FIPS 204", "5", "2,592 B", "4,896 B", "4,627 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-128f", "FIPS 205", "1", "32 B", "64 B", "~17,088 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-128s", "FIPS 205", "1", "32 B", "64 B", "~7,856 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-192f", "FIPS 205", "3", "48 B", "96 B", "~35,664 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-192s", "FIPS 205", "3", "48 B", "96 B", "~16,224 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-256f", "FIPS 205", "5", "64 B", "128 B", "~49,856 B (signature)", "Yes"],
    ["SLH-DSA-SHA2-256s", "FIPS 205", "5", "64 B", "128 B", "~29,792 B (signature)", "Yes"],
]


def _build_pdf_buffer() -> BytesIO:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("PQC Shield — NIST Algorithm Compliance Report", styles["Title"])]
    story.append(Paragraph("Supported algorithms and key/signature sizes.", styles["Normal"]))
    story.append(Paragraph(" ", styles["Normal"]))
    t = Table(COMPLIANCE_ROWS, colWidths=[1.4 * inch, 1.1 * inch, 0.9 * inch, 1.0 * inch, 1.0 * inch, 1.5 * inch, 0.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return buf


@router.get("/report", response_class=Response)
async def get_compliance_report(
    _: User = Depends(get_current_user),
) -> Response:
    """Generate and download the compliance report as PDF."""
    if not REPORTLAB_AVAILABLE:
        return Response(
            content=b"PDF generation unavailable (reportlab not installed).",
            status_code=503,
            media_type="text/plain",
        )
    buf = _build_pdf_buffer()
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=pqc-shield-compliance-report.pdf"},
    )
