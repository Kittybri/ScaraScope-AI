"""Deterministic, dependency-light retrieval for public SEC filing passages."""
from .lexical import EvidencePassage, chunk_sections, search_passages

__all__ = ["EvidencePassage", "chunk_sections", "search_passages"]
