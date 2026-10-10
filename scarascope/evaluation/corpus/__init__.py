"""Versioned SEC filing snapshots and reviewer-gated document QA benchmarking."""
from .snapshots import FilingSnapshot, make_snapshot, load_snapshot, save_snapshot
from .annotations import Annotation, load_annotations, validate_annotations
from .scoring import compare_corpus

__all__ = ["FilingSnapshot", "make_snapshot", "load_snapshot", "save_snapshot",
           "Annotation", "load_annotations", "validate_annotations", "compare_corpus"]
