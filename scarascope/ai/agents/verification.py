"""Checks arithmetic and provenance. Does NOT certify free-form LLM prose."""
from math import isclose
from pydantic import BaseModel, Field
from ...core.models import AnnualFinancials
from ...finance.calculations import ratio_pct
from ...data.sec.filings import EvidenceSnippet, FilingSection

class VerificationResult(BaseModel):
    passed: bool
    checks: int
    issues: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda:[
        "These checks validate arithmetic and source metadata, not the semantic truth of arbitrary AI-written claims.",
        "SEC XBRL tag mapping and filing text segmentation require human review for material decisions.",
    ])

def verify_financials(rows: list[AnnualFinancials], synthetic: bool = False) -> VerificationResult:
    issues = []
    checks = 0
    for index, row in enumerate(rows):
        for label, value in (("operating margin",row.operating_margin_pct),("net margin",row.net_margin_pct)):
            expected = ratio_pct(row.operating_income if label.startswith("operating") else row.net_income,row.revenue)
            checks += 1
            if value != expected:
                issues.append(f"{row.period_end}: {label} disagrees with reported inputs.")
        if index + 1 < len(rows):
            previous = rows[index + 1]
            checks += 1
            if previous.revenue and previous.revenue > 0 and row.revenue is not None:
                expected = ratio_pct(row.revenue - previous.revenue, previous.revenue)
                if row.revenue_growth_pct != expected:
                    issues.append(f"{row.period_end}: growth rate does not match adjacent revenue.")
        for source in row.sources:
            checks += 1
            if not source.source_url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")) or not source.accession:
                issues.append(f"{row.period_end}: questionable provenance for {source.metric}.")
        if not synthetic and row.revenue is not None and not any(s.metric=="revenue" for s in row.sources):
            issues.append(f"{row.period_end}: revenue has no SEC source entry.")
    return VerificationResult(passed=not issues,checks=checks,issues=issues)

def verify_excerpts(sections: list[FilingSection], excerpts: list[EvidenceSnippet]) -> VerificationResult:
    issues = []
    checks = 0
    for excerpt in excerpts:
        checks += 1
        if not any(excerpt.excerpt in " ".join(section.text.split()) and
                   excerpt.filing_url == section.filing_url and excerpt.accession == section.accession
                   for section in sections):
            issues.append(f"Excerpt not found in retrieved {excerpt.item} content.")
    return VerificationResult(passed=not issues,checks=checks,issues=issues)
