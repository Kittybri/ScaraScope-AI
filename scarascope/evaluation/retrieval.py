"""Deterministic retrieval regression suite; not a real-world accuracy benchmark."""
from ..ai.retrieval import chunk_sections, search_passages
from ..data.sec.filings import FilingSection


def evaluate_retrieval() -> dict:
    sections = [
        FilingSection(item="Item 1A", title="Risk Factors", filing_url="https://example.invalid/test",
                      accession="TEST", filed="2026-01-01", locator="Synthetic risk section",
                      text="Cybersecurity incidents may disrupt online services and leak customer information. "
                           "Supply chain disruption can delay delivery of hardware products."),
        FilingSection(item="Item 7", title="Management Discussion and Analysis", filing_url="https://example.invalid/test",
                      accession="TEST", filed="2026-01-01", locator="Synthetic MD&A section",
                      text="Subscription revenue grew because of customer demand and higher renewal rates. "
                           "Infrastructure operating expenses increased due to data center expansion."),
    ]
    passages = chunk_sections(sections)
    cases = [
        ("What cybersecurity problems are disclosed?", "Item 1A"),
        ("How is subscription revenue changing?", "Item 7"),
        ("What supply chain disruptions are mentioned?", "Item 1A"),
        ("Why are data center expenses increasing?", "Item 7"),
        ("Where are moon colonies discussed?", None),
    ]
    outcomes = []
    for question, expected in cases:
        hits = search_passages(passages, question, limit=1)
        actual = hits[0].item if hits else None
        outcomes.append({"question": question, "expected_section": expected,
                         "retrieved_section": actual, "passed": actual == expected})
    return {"passed": sum(row["passed"] for row in outcomes), "total": len(outcomes),
            "cases": outcomes,
            "scope": "Synthetic lexical retrieval and abstention tests, NOT live SEC or LLM QA accuracy."}
