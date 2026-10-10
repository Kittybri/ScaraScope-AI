"""Offline, read-only evidence review packet. No client JavaScript or remote assets.

By default this is a BLIND packet: no gold answers, gold passage IDs, answerable
labels or reviewer opinions are included, even if annotations already have them.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from ...ai.retrieval import chunk_sections
from .annotations import Annotation, validate_annotations
from .snapshots import FilingSnapshot


STYLE = """
body{font:16px/1.55 system-ui,sans-serif;background:#f5f8fb;color:#10243d;margin:0}
main{max-width:1050px;margin:0 auto;padding:36px 22px}
h1,h2,h3{line-height:1.2}h1{font-size:2.4rem}h2{padding-top:12px}
.banner{background:#12283e;color:#eaf8fa;padding:25px;border-radius:14px}
.banner small{color:#8ce2cf}.note{border-left:4px solid #148675;padding:12px 18px;background:#e8f4f0}
.card{background:white;border:1px solid #d9e5ed;border-radius:12px;padding:19px;margin:17px 0}
.meta{color:#4c6579;font-size:.9rem}a{color:#087968}code{overflow-wrap:anywhere}
.passage{border-top:1px solid #e7eef5;margin-top:14px;padding-top:12px}
blockquote{white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0;color:#293e55}
.questions{padding-left:25px}.questions li{margin:10px 0}
@media print{.card{break-inside:avoid}body{background:white}main{padding:0}}
"""


def render_review_packet(snapshots: list[FilingSnapshot], annotations: list[Annotation],
                         *, max_passages_per_filing: int = 36) -> str:
    if not 1 <= max_passages_per_filing <= 150:
        raise ValueError("Review packet requires 1–150 excerpts per filing.")
    validate_annotations(annotations, snapshots)
    grouped = {}
    for a in annotations:
        grouped.setdefault((a.cik,a.accession),[]).append(a)
    sections=[]
    for snap in snapshots:
        questions = grouped.get((snap.cik,snap.accession),[])
        if not questions:
            continue
        passages = chunk_sections(snap.sections)
        visible = passages[:max_passages_per_filing]
        qitems = ''.join(f'<li><code>{escape(q.id)}</code> {escape(q.question)}</li>' for q in questions)
        cards=[]
        for passage in visible:
            cards.append('<div class="passage"><div class="meta">'
                         f'<strong>{escape(passage.item)}</strong> · '
                         f'Passage <code>{escape(passage.evidence_id)}</code> · '
                         f'Normalized offset {passage.start_char}</div>'
                         f'<blockquote>{escape(passage.excerpt)}</blockquote></div>')
        sections.append('<section class="card">'
            f'<h2>CIK {escape(snap.cik)} · {escape(snap.form)}</h2>'
            f'<div class="meta">Accession {escape(snap.accession)} · '
            f'Filed {escape(snap.sections[0].filed)} · '
            f'Text hash <code>{escape(snap.text_sha256)}</code></div>'
            f'<p><a href="{escape(snap.filing_url,quote=True)}" rel="noopener noreferrer">'
            'Open original SEC filing</a> (filing-level link, not a paragraph anchor)</p>'
            '<h3>Questions for independent review</h3><ol class="questions">'
            f'{qitems}</ol><h3>Exact extracted passages</h3>'
            f'<p class="meta">Showing {len(visible)} of {len(passages)} passages. '
            'Use CLI inventory --all-passages for all evidence IDs.</p>'
            + ''.join(cards) + '</section>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>ScaraScope evidence review packet</title>'
            f'<style>{STYLE}</style></head><body><main>'
            '<div class="banner"><small>SCARASCOPE · INDEPENDENT REVIEW</small>'
            '<h1>SEC Evidence Review Packet</h1><p>Read-only, unscored source review.</p></div>'
            '<p class="note">This document contains untrusted excerpts from SEC filings. '
            'It does not attest that any question has been answered correctly, or that a reviewer '
            'has confirmed a label. Gold answers, answerability flags and reviewer notes are '
            'intentionally hidden to reduce anchoring bias. Check the original SEC filing '
            'before signing off.</p>'
            + ''.join(sections) + '</main></body></html>')


def save_review_packet(html: str, target: Path) -> Path:
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError("Review packet exists; preserve the original and use a new output name.")
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as stream:
        stream.write(html)
    return target
