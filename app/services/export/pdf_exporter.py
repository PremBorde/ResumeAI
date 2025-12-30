from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@dataclass(frozen=True)
class PdfExportResult:
    filename: str
    content_type: str
    data: bytes


def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip().replace(" ", "_")


def export_pdf_report(*, analysis: dict[str, Any], resume: dict[str, Any]) -> PdfExportResult:
    """Generate a professional PDF report with visualizations."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required for PDF export. Install with: pip install reportlab")

    analysis_id = analysis.get("analysis_id") or "analysis"
    score = analysis.get("score", {})
    skill_gap = analysis.get("skill_gap", {})
    suggestions = analysis.get("suggestions", {})
    ats = analysis.get("ats", {})

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#00e5cc'),
        spaceAfter=30,
    )
    story.append(Paragraph("Resume Match Analysis Report", title_style))
    story.append(Spacer(1, 0.2*inch))

    # Score Section
    final_score = score.get("final_match_score", 0)
    semantic_score = score.get("semantic_similarity_score", 0)
    skill_score = score.get("skill_overlap_score", 0)

    story.append(Paragraph(f"<b>Overall Match Score: {final_score:.1f}%</b>", styles['Heading2']))
    
    score_data = [
        ['Metric', 'Score'],
        ['Semantic Similarity', f'{semantic_score:.1f}%'],
        ['Skill Overlap', f'{skill_score:.1f}%'],
    ]
    score_table = Table(score_data, colWidths=[4*inch, 2*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a26')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#12121a')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#00e5cc')),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.3*inch))

    # Skill Gap Analysis
    story.append(Paragraph("<b>Skill Gap Analysis</b>", styles['Heading2']))
    
    matching = skill_gap.get("matching_skills", [])
    missing = skill_gap.get("missing_required_skills", [])
    nice_to_have = skill_gap.get("nice_to_have_skills", [])

    story.append(Paragraph(f"<b>Matching Skills ({len(matching)}):</b>", styles['Normal']))
    if matching:
        story.append(Paragraph(", ".join(matching[:15]), styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph(f"<b>Missing Required Skills ({len(missing)}):</b>", styles['Normal']))
    if missing:
        story.append(Paragraph(", ".join(missing[:15]), styles['Normal']))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph(f"<b>Nice to Have Skills ({len(nice_to_have)}):</b>", styles['Normal']))
    if nice_to_have:
        story.append(Paragraph(", ".join(nice_to_have[:15]), styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # ATS Score
    ats_score = ats.get("overall_score", 0)
    story.append(Paragraph(f"<b>ATS Readiness Score: {ats_score:.1f}%</b>", styles['Heading2']))
    if ats.get("recommendations"):
        story.append(Paragraph("<b>Recommendations:</b>", styles['Normal']))
        for rec in ats["recommendations"][:5]:
            story.append(Paragraph(f"• {rec}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # AI Recommendations
    if suggestions:
        story.append(Paragraph("<b>AI Recommendations</b>", styles['Heading2']))
        if suggestions.get("key_strengths"):
            story.append(Paragraph("<b>Key Strengths:</b>", styles['Normal']))
            for strength in suggestions["key_strengths"][:5]:
                story.append(Paragraph(f"• {strength}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    filename = _safe_filename(f"resume_analysis_{analysis_id}.pdf")
    return PdfExportResult(
        filename=filename,
        content_type="application/pdf",
        data=buffer.getvalue(),
    )




