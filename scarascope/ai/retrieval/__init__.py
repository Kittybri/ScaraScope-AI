"""Deterministic, dependency-light retrieval for public SEC filing passages."""
from .lexical import EvidencePassage, chunk_sections, search_passages
from .bm25 import search_bm25
from .semantic import LocalSentenceEncoder, search_semantic
from .hybrid import search_hybrid

__all__ = ["EvidencePassage", "chunk_sections", "search_passages", "search_bm25", "LocalSentenceEncoder", "search_semantic", "search_hybrid"]
