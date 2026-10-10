"""Generate a PDF using a verified structured agent report; no raw HTML injections."""
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from ..services.agent import AgentReport


def export_pdf(report: AgentReport) -> bytes:
    out = BytesIO()
    doc = SimpleDocTemplate(out,pagesize=letter,rightMargin=38,leftMargin=38,topMargin=40,bottomMargin=42)
    styles = getSampleStyleSheet()
    story = [Paragraph("ScaraScope AI | Financial Research", styles["Title"]),
             Paragraph(escape(f"{report.research.company} ({report.research.ticker})"),styles["Heading2"]),
             Paragraph(escape(f"Generated {report.generated_at.date()} | Data: {report.research.data_kind}"),styles["Normal"]),Spacer(1,14),
             Paragraph("Executive summary",styles["Heading2"]),Paragraph(escape(report.executive_summary),styles["BodyText"]),Spacer(1,12),
             Paragraph("Annual financial figures (USD)",styles["Heading2"])]
    data = [["Period", "Revenue", "Operating income", "Net income", "Op. margin"]]
    for row in report.research.financials:
        data.append([row.period_end.isoformat(),*(f"{getattr(row,k):,.0f}" if getattr(row,k) is not None else "N/A" for k in ("revenue","operating_income","net_income")),
                     f"{row.operating_margin_pct:.2f}%" if row.operating_margin_pct is not None else "N/A"])
    table = Table(data,repeatRows=1,hAlign="LEFT",colWidths=[87,102,102,102,78])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#112c46")),
                               ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                               ("FONTSIZE",(0,0),(-1,-1),8),
                               ("BOTTOMPADDING",(0,0),(-1,-1),7),
                               ("LINEBELOW",(0,1),(-1,-1),0.3,colors.lightgrey)]))
    story.extend([table,Spacer(1,12),Paragraph("Sources & evidence",styles["Heading2"])])
    seen = set()
    for row in report.research.financials:
        for src in row.sources:
            key=(src.source_url,src.metric)
            if key in seen:continue
            seen.add(key)
            story.append(Paragraph(escape(f"{src.period_end}: {src.metric}, accession {src.accession}, {src.source_url}"),styles["BodyText"]))
            if len(seen)>=14:break
        if len(seen)>=14:break
    for excerpt in report.filing.evidence[:4]:
        story.append(Paragraph(escape(f"{excerpt.locator} ({excerpt.accession})"),styles["Heading4"]))
        story.append(Paragraph(escape(excerpt.excerpt[:500]),styles["BodyText"]))
        story.append(Paragraph(escape(excerpt.filing_url),styles["Normal"]))
    story.extend([Spacer(1,12),Paragraph("Limitations",styles["Heading2"])])
    for note in report.limitations[:10]:story.append(Paragraph("- "+escape(note),styles["BodyText"]))
    story.append(Paragraph("Research demonstration only. Not investment advice. Verify material facts against SEC originals.",styles["Italic"]))
    doc.build(story)
    return out.getvalue()
