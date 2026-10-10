"""Read public 10-K and 10-Q sections; URLs derived only from official SEC submissions.

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


_SECTION_RE = re.compile(r"(?im)^\s*item\s+(1a|1b|7a|7|2|3|4|8)\s*[.\-:\u2013]?\s*(.*)$")
_TITLES = {"1a":"Risk Factors", "7":"Management Discussion and Analysis"}

def extract_sections(html: str, filing_url: str, accession: str, filed: str, form: str = "10-K") -> list[FilingSection]:
    parser = _TextExtractor()
    parser.feed(html[:MAX_HTML_BYTES])
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.text).splitlines() if line.strip())
    # Filing tables of contents repeat headings. Prefer the section occurrence with longest
    # plausible content, and reject tiny TOC references.
    matches = list(_SECTION_RE.finditer(text))
    results = []
    if form not in {"10-K", "10-Q"}:
        raise ValueError("Unsupported filing form.")
    titles = _TITLES if form == "10-K" else {"2": "Management Discussion and Analysis", "1a": "Risk Factors"}
    for item, title in titles.items():
        candidates = []
        for index, match in enumerate(matches):
            if match.group(1).lower() != item:
                continue
            end = matches[index+1].start() if index+1 < len(matches) else len(text)
            candidate = text[match.end():end].strip()
            if 250 <= len(candidate) <= 1_500_000:
                candidates.append(candidate)
        if candidates:
            chosen = max(candidates, key=len)[:240_000]
            results.append(FilingSection(item=f"Item {item.upper()}", title=title, text=chosen,
                                         filing_url=filing_url, accession=accession, filed=filed,
                                         locator=f"{form}, Item {item.upper()} (section-level; passage offset is in extracted text, not an SEC deep link)"))
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

    async def research(self, cik: str, question: str, limit: int = 4, form: str = "10-K",
                       accession: str | None = None) -> FilingResearch:
        """Fetch newest or accession-pinned SEC filing, never a caller-supplied URL.

        Pinned accessions must be present in the issuer's SEC submission manifest.
        If the chosen accession is absent, do not silently fall back to latest.
        """
        from .submissions import choose_record, archive_index_names, ACCESSION_PATTERN

        if form not in {"10-K", "10-Q"}:
            raise SECError("Supported forms are 10-K and 10-Q.")
        if not self.user_agent or "@" not in self.user_agent or "example.com" in self.user_agent.lower():
            raise SECError("Set a real SEC_USER_AGENT with contact email for SEC filings.")
        if not re.fullmatch(r"\d{1,10}", cik):
            raise SECError("Invalid CIK.")
        if accession is not None and not re.fullmatch(ACCESSION_PATTERN, accession):
            raise SECError("Invalid accession number; expected 0000000000-00-000000.")
        padded = cik.zfill(10)
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, headers={
            "User-Agent": self.user_agent, "Accept": "application/json,text/html"}) as client:
            try:
                await SEC_GATE.wait()
                r = await client.get(SUBMISSIONS_URL.format(cik=padded))
                r.raise_for_status()
                if len(r.content) > MAX_HTML_BYTES:
                    raise SECError("SEC submissions index exceeds the size cap.")
                submissions = r.json()
                record = choose_record(submissions["filings"]["recent"], form, accession)
                if accession is not None and record is None:
                    for filename in archive_index_names(submissions, padded):
                        # Whitelisted SEC archive index name, never constructed from user input.
                        await SEC_GATE.wait()
                        archived = await client.get(f"https://data.sec.gov/submissions/{filename}")
                        archived.raise_for_status()
                        if len(archived.content) > MAX_HTML_BYTES:
                            raise SECError("SEC historical submissions index exceeds the size cap.")
                        record = choose_record(archived.json(), form, accession)
                        if record is not None:
                            break
                if record is None:
                    notice = ("Requested SEC filing accession is not listed for this CIK/form. No substitute filing was used."
                              if accession else "No matching recent 10-K or 10-Q was found.")
                    return FilingResearch(cik=padded, warnings=[notice])
                url = record.url(padded)
                # Stream instead of buffering an arbitrarily large SEC document in memory.
                await SEC_GATE.wait()
                content = bytearray()
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    async for part in response.aiter_bytes():
                        content.extend(part)
                        if len(content) > MAX_HTML_BYTES:
                            raise SECError("SEC filing exceeds the configured document size limit.")
                # SEC primary documents may contain legacy encodings. Replacement is explicit.
                html = content.decode("utf-8", errors="replace")
                sections = extract_sections(html, url, record.accession, record.filed, form=form)
                result = FilingResearch(cik=padded, accession=record.accession,
                                        filing_url=url, sections=sections,
                                        evidence=retrieve_evidence(sections, question, limit))
                if not sections:
                    result.warnings.append("Could not locate supported filing sections; extraction is best-effort.")
                return result
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                return FilingResearch(cik=padded, warnings=[
                    "SEC filing text or submissions metadata is temporarily unavailable; no alternate filing was substituted."])
