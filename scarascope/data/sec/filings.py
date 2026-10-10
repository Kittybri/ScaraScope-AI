"""Read specific public 10-K sections; URLs derived only from official SEC submissions.

This is conservative section extraction, NOT full paragraph-anchored filing RAG.
SEC HTML varies widely; unavailable sections are reported instead of invented.
"""
import re
from html.parser import HTMLParser
from typing import Any
import httpx
from pydantic import BaseModel, Field
from .client import SECError
from .fair_access import SEC_GATE

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
MAX_HTML_BYTES = 5_000_000

class FilingSection(BaseModel):
    item: str
    title: str
    text: str
    filing_url: str
    accession: str
    filed: str
    locator: str

class EvidenceSnippet(BaseModel):
    item: str
    excerpt: str
    filing_url: str
    locator: str
    accession: str
    relevance_score: int = 0

class FilingResearch(BaseModel):
    cik: str
    accession: str | None = None
    filing_url: str | None = None
    sections: list[FilingSection] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        elif not self.skip and tag in {"p", "div", "br", "tr", "h1", "h2", "h3", "table", "li"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript"}:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in {"p", "div", "tr", "h1", "h2", "h3", "li"}:
            self.text.append("\n")

    def handle_data(self, data: str):
        if not self.skip:
            self.text.append(data)


_SECTION_RE = re.compile(r"(?im)^\s*item\s+(1a|1b|7|7a|8)\s*[.\-:\u2013]?\s*(.*)$")
_TITLES = {"1a":"Risk Factors", "7":"Management Discussion and Analysis"}

def extract_sections(html: str, filing_url: str, accession: str, filed: str) -> list[FilingSection]:
    parser = _TextExtractor()
    parser.feed(html[:MAX_HTML_BYTES])
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.text).splitlines() if line.strip())
    # Filing tables of contents repeat headings. Prefer the section occurrence with longest
    # plausible content, and reject tiny TOC references.
    matches = list(_SECTION_RE.finditer(text))
    results = []
    for item, title in _TITLES.items():
        candidates = []
        for index, match in enumerate(matches):
            if match.group(1).lower() != item:
                continue
            end = matches[index+1].start() if index+1 < len(matches) else len(text)
            candidate = text[match.end():end].strip()
            if 250 <= len(candidate) <= 1_500_000:
                candidates.append(candidate)
        if candidates:
            chosen = max(candidates, key=len)[:45_000]
            results.append(FilingSection(item=f"Item {item.upper()}", title=title, text=chosen,
                                         filing_url=filing_url, accession=accession, filed=filed,
                                         locator=f"10-K, Item {item.upper()} (section-level, not paragraph anchor)"))
    return results

_STOPWORDS = {"what","the","about","have","from","with","this","that","their","which","please","analyze","company","financial","report","risk","risks","and","for","how","are","into"}

def retrieve_evidence(sections: list[FilingSection], question: str, limit: int = 4) -> list[EvidenceSnippet]:
    terms = set(re.findall(r"[a-z]{4,}", question.lower())) - _STOPWORDS
    scored: list[EvidenceSnippet] = []
    for section in sections:
        paragraphs = [" ".join(p.split()) for p in section.text.split("\n")]
        for paragraph in paragraphs:
            if len(paragraph) < 80:
                continue
            for start in range(0, len(paragraph), 900):
                chunk = paragraph[start:start+1100]
                score = sum(term in chunk.lower() for term in terms)
                if score or not terms:
                    scored.append(EvidenceSnippet(item=section.item, excerpt=chunk,
                                                  filing_url=section.filing_url, accession=section.accession,
                                                  locator=section.locator, relevance_score=score))
    scored.sort(key=lambda x: (-x.relevance_score, x.item, x.excerpt))
    return scored[:max(1, min(8, limit))]

class FilingClient:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    async def research(self, cik: str, question: str, limit: int = 4) -> FilingResearch:
        if not self.user_agent or "@" not in self.user_agent or "example.com" in self.user_agent.lower():
            raise SECError("Set a real SEC_USER_AGENT with contact email for SEC filings.")
        if not re.fullmatch(r"\d{1,10}", cik):
            raise SECError("Invalid CIK.")
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, headers={
            "User-Agent": self.user_agent, "Accept": "application/json,text/html"}) as client:
            try:
                await SEC_GATE.wait()
                r = await client.get(SUBMISSIONS_URL.format(cik=cik.zfill(10)))
                r.raise_for_status()
                payload = r.json()
                recent = payload["filings"]["recent"]
                forms = recent["form"]
                ix = next(i for i, form in enumerate(forms) if form == "10-K")
                accession = str(recent["accessionNumber"][ix])
                document = str(recent["primaryDocument"][ix])
                filed = str(recent["filingDate"][ix])
                if not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession):
                    raise SECError("SEC submission returned an unexpected accession number.")
                if not re.fullmatch(r"[A-Za-z0-9_.-]{1,130}\.(?:htm|html|txt)", document, re.I):
                    raise SECError("SEC submission returned an unsafe primary document path.")
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"
                await SEC_GATE.wait()
                resp = await client.get(url)
                resp.raise_for_status()
                if len(resp.content) > MAX_HTML_BYTES:
                    raise SECError("SEC filing exceeds the configured document size limit.")
                sections = extract_sections(resp.text, url, accession, filed)
                result = FilingResearch(cik=cik.zfill(10), accession=accession, filing_url=url, sections=sections,
                                        evidence=retrieve_evidence(sections, question, limit))
                if not sections:
                    result.warnings.append("Could not locate complete Item 1A/7 sections. Source formatting varies; no narrative claims were generated.")
                return result
            except (httpx.HTTPError, KeyError, TypeError, ValueError, StopIteration) as exc:
                return FilingResearch(cik=cik.zfill(10), warnings=["SEC filing text is temporarily unavailable or no recent 10-K was found."])
