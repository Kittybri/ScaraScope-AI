from datetime import date
import pytest

from scarascope.sec import SECClient, SECError, extract_annual_financials


def annual(end: str, start: str, val: int, accession: str, filed: str = "2026-02-01"):
    return {"form": "10-K", "end": end, "start": start, "val": val, "accn": accession, "filed": filed}


def test_extract_periods_latest_restated_and_avoid_quarters():
    facts = {"cik": 123456, "facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            annual("2024-12-31", "2024-01-01", 100, "0001-24-000001", "2025-02-01"),
            annual("2024-12-31", "2024-01-01", 110, "0001-25-000001", "2026-02-01"),
            annual("2025-12-31", "2025-01-01", 130, "0001-25-000002"),
            annual("2025-09-30", "2025-07-01", 42, "0001-25-000003"),
        ]}},
        "OperatingIncomeLoss": {"units": {"USD": [
            annual("2025-12-31", "2025-01-01", 20, "0001-25-000002"),
            annual("2024-12-31", "2024-03-01", 25, "0001-25-000002"),
        ]}},
        "Assets": {"units": {"USD": [{"form": "10-K", "end": "2025-12-31", "val": 900, "accn": "0001-25-000002", "filed": "2026-02-01"}]}}
    }}}
    rows = extract_annual_financials(facts, years=3)
    assert [r.period_end for r in rows] == [date(2025, 12, 31), date(2024, 12, 31)]
    assert rows[0].revenue == 130
    assert rows[0].assets == 900
    assert rows[1].revenue == 110
    assert rows[1].operating_income is None  # mismatched start dates
    assert rows[0].sources[0].source_url.startswith("https://www.sec.gov/Archives/")


@pytest.mark.asyncio
async def test_requires_real_sec_contact():
    with pytest.raises(SECError, match="SEC_USER_AGENT"):
        await SECClient("ScaraScopeAI fake@example.com").get_company("MSFT", 3)
