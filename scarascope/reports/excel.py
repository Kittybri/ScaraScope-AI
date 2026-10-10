"""Financial workbook, calculation formulas, original sources, and warnings."""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from ..services.agent import AgentReport


def safe_cell(value):
    if isinstance(value,str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def export_excel(report: AgentReport) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Financials"
    ws.append(["Period end", "Revenue USD", "Operating income USD", "Net income USD", "YoY growth", "Operating margin", "Net margin"])
    for index, row in enumerate(report.research.financials, start=2):
        ws.append([row.period_end.isoformat(),row.revenue,row.operating_income,row.net_income,None,None,None])
        if row.revenue is not None and row.operating_income is not None:
            ws.cell(index,6,f'=IFERROR(C{index}/B{index},"")')
        if row.revenue is not None and row.net_income is not None:
            ws.cell(index,7,f'=IFERROR(D{index}/B{index},"")')
        if index > 2 and row.revenue is not None and report.research.financials[index-3].revenue is not None:
            ws.cell(index-1,5,f'=IFERROR(B{index-1}/B{index}-1,"")')
        for column in (5,6,7): ws.cell(index,column).number_format="0.00%"
    for i in range(2,max(2,ws.max_row)):
        ws.cell(i,5).number_format="0.00%"
    src = wb.create_sheet("SEC Sources")
    src.append(["Period","Metric","Form","Accession","Filed","URL"])
    for row in report.research.financials:
        for item in row.sources:
            src.append([row.period_end.isoformat(),item.metric,item.form,item.accession,item.filed,item.source_url])
    ev = wb.create_sheet("Narrative Evidence")
    ev.append(["Filing item", "Excerpt", "Source locator", "Filing URL"])
    for quote in report.filing.evidence:
        ev.append([quote.item,safe_cell(quote.excerpt),quote.locator,quote.filing_url])
    notes = wb.create_sheet("Caveats")
    notes.append(["Source",report.research.data_source]);notes.append(["Financial verification passed",str(report.verification.passed)])
    for caveat in report.limitations:notes.append([safe_cell(caveat)])
    notes.append(["Notice","Illustrative research; no investment recommendation. Ratios are independent Python calculations; workbook formula cells recalculate in Excel."])
    for sheet in wb:
        sheet.freeze_panes="A2"
        for cell in sheet[1]:
            cell.font=Font(color="FFFFFF",bold=True)
            cell.fill=PatternFill(fill_type="solid",fgColor="15334D")
        for column in sheet.columns:
            letter=column[0].column_letter
            max_len=max(len(str(c.value or "")) for c in column)
            sheet.column_dimensions[letter].width=min(65,max(16,max_len+3))
    data=BytesIO(); wb.save(data);return data.getvalue()
