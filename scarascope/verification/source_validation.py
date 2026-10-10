"""SEC source metadata checks, not proof that a filing endorses every narrative claim."""
import re
from urllib.parse import urlsplit
from ..core.models import AnnualFinancials

_ACCESSION = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")


def check_financial_sources(rows: list[AnnualFinancials]) -> list[str]:
    problems = []
    for row in rows:
        mapped = {}
        for source in row.sources:
            mapped.setdefault(source.metric, []).append(source)
            parsed = urlsplit(source.source_url)
            if parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "data.sec.gov"} or parsed.username or parsed.password or parsed.port:
                problems.append(f"{row.period_end}: invalid SEC domain for {source.metric}.")
            if not _ACCESSION.fullmatch(source.accession):
                problems.append(f"{row.period_end}: invalid accession number for {source.metric}.")
            if source.form != "10-K" or source.period_end != row.period_end:
                problems.append(f"{row.period_end}: {source.metric} filing form or period mismatch.")
            if source.filed and source.filed < row.period_end.isoformat():
                problems.append(f"{row.period_end}: {source.metric} filing predates reporting period.")
        for metric in ("revenue", "operating_income", "net_income"):
            if getattr(row, metric) is not None and len(mapped.get(metric, [])) != 1:
                problems.append(f"{row.period_end}: {metric} must have exactly one source record.")
    return problems
