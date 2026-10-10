"""Load frozen QA questions and reproduce bounded text fixtures from cited SEC values.

Documents here are *reconstructed reference-table extracts*, NOT raw SEC HTML,
not live ingestion and not a curated corpus of full public 10-K filings.
The question split is held out; the underlying 2021-24 figures are shared.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ...data.sec.filings import FilingSection
from ..financial_accuracy import load_reference

DATA_DIR = Path(__file__).resolve().parents[1] / 'datasets'
SUPPORTED_METRICS = {'revenue': 'Revenue', 'operating_income': 'Operating income', 'net_income': 'Net income'}


class QACase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9_]{6,64}$')
    split: Literal['dev', 'heldout']
    question: str = Field(min_length=12, max_length=240)
    answerable: bool
    gold_document_id: str | None = None
    gold_answer: int | None = None
    gold_source_url: str | None = None
    gold_accession: str | None = None
    unit: Literal['USD_millions'] = 'USD_millions'

    @model_validator(mode='after')
    def valid_gold(self):
        metadata = (self.gold_document_id, self.gold_answer, self.gold_source_url, self.gold_accession)
        if self.answerable != all(x is not None for x in metadata):
            raise ValueError('Answerable questions require all gold fields; unanswerable questions must omit them.')
        return self


def load_questions(split: Literal['dev', 'heldout'], folder: Path = DATA_DIR) -> tuple[list[QACase], str]:
    path = folder / f'qa_{split}_v1.jsonl'
    raw = path.read_bytes()
    if len(raw) > 200_000:
        raise ValueError('Question dataset too large.')
    rows = [QACase.model_validate(json.loads(line)) for line in raw.decode('utf-8').splitlines() if line.strip()]
    ids = [row.id for row in rows]
    if not rows or len(ids) != len(set(ids)) or any(row.split != split for row in rows):
        raise ValueError('Empty, duplicate, or incorrectly partitioned QA dataset.')
    return rows, sha256(raw).hexdigest()


def reference_sections(reference: dict | None = None) -> tuple[list[FilingSection], dict[str, dict]]:
    """Exactly one distinct synthetic section per company/year/metric, with source metadata."""
    reference = reference or load_reference()[0]
    sections: list[FilingSection] = []
    documents: dict[str, dict] = {}
    for company in reference['companies']:
        source = company['source']
        for row in company['rows']:
            for metric, label in SUPPORTED_METRICS.items():
                document_id = f"{company['ticker']}-{row['fiscal_year']}-{metric}"
                # No fabricated management statements or made-up original SEC quotations.
                excerpt = (f"{company['name']} {company['ticker']}. Fiscal year {row['fiscal_year']} "
                           f"ending {row['period_end']}. {label}: USD {row[metric]:,} million. "
                           f"This amount is a reconstructed reference-table extract, not raw filing text.")
                section = FilingSection(item=document_id, title=source['table'], text=excerpt,
                    filing_url=source['url'], accession=source['accession'], filed=source['filed'],
                    locator=f"{source['form']} {source['table']} / FY{row['fiscal_year']} / {label}")
                sections.append(section)
                documents[document_id] = {'value': row[metric], 'source_url':source['url'],
                                          'accession':source['accession'], 'text':excerpt}
    return sections, documents


def validate_gold(cases: list[QACase], docs: dict[str, dict]) -> None:
    for case in cases:
        if not case.answerable:
            continue
        doc = docs.get(case.gold_document_id)
        if not doc or doc['value'] != case.gold_answer or doc['source_url'] != case.gold_source_url \
                or doc['accession'] != case.gold_accession:
            raise ValueError(f'Gold reference mismatch: {case.id}')
