from scarascope.data.sec.filings import extract_sections, retrieve_evidence
from scarascope.ai.agents.verification import verify_excerpts,verify_financials
from scarascope.core.models import AnnualFinancials,FactSource
from scarascope.finance.calculations import enrich_financials
from datetime import date

HTML="""<html><body>
<p>Table of Contents</p><p>Item 1A Risk Factors</p><p>3</p>
<p>Item 7 Management's Discussion and Analysis</p><p>8</p>
<p>Item 1A. Risk Factors</p>
<p>Cybersecurity interruptions, cloud disruption, operational failures, data privacy issues, and supply chain uncertainty may materially affect the business and its operating results. These risks could reduce revenue and impair our reputation.</p>
<p>Supply chain disruptions and regulatory actions could also affect our ability to operate in international markets, manufacture products on schedule, or recover receivables.</p>
<p>Item 1B. Unresolved Staff Comments</p><p>Nothing disclosed here.</p>
<p>Item 7. Management Discussion and Analysis</p>
<p>Revenue and operating margin increased during the year, driven by enterprise demand and pricing improvements, while infrastructure expenses increased. Management expects uncertainty to continue in the next fiscal year.</p>
<p>Management believes these developments have impacted liquidity, profitability, research and development spending, and capital allocation. We do not know the future rate of demand growth.</p>
<p>Item 7A. Quantitative and Qualitative Disclosures</p>
</body></html>"""

def test_filing_sections_skip_toc_and_retrieve_excerpts():
    sections=extract_sections(HTML,"https://www.sec.gov/fake","0000000001-26-000001","2026-01-01")
    assert len(sections)==2
    assert sections[0].item=="Item 1A"
    assert "Cybersecurity interruptions" in sections[0].text
    excerpts=retrieve_evidence(sections,"cybersecurity and supply chain risks")
    assert excerpts
    assert verify_excerpts(sections,excerpts).passed


def test_verified_excerpt_rejects_fabrications():
    sections=extract_sections(HTML,"https://www.sec.gov/fake","a","2026-01-01")
    excerpt=retrieve_evidence(sections,"cybersecurity")[0]
    assert verify_excerpts(sections,[excerpt.model_copy(update={"excerpt":"Fabricated claim, not in filing."})]).passed is False


def test_arithmetic_verifier_catches_tampering():
    row=AnnualFinancials(fiscal_year=2025,period_end=date(2025,12,31),revenue=200,operating_income=40,net_income=20,
                         sources=[FactSource(metric="revenue",form="10-K",accession="0000000001-26-000001",filed="2026-01-01",period_end=date(2025,12,31),source_url="https://www.sec.gov/Archives/foo")])
    enrich_financials([row]);assert verify_financials([row]).passed
    row.operating_margin_pct=97
    assert not verify_financials([row]).passed
