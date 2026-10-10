"""Deterministic, dependency-light retrieval for public SEC filing passages."""
from .lexical import EvidencePassage, chunk_sections, search_passages
from .bm25 import search_bm25

__all__ = ["EvidencePassage", "chunk_sections", "search_passages", "search_bm25"]
