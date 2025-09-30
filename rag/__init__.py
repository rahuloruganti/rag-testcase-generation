"""Simplified procedural RAG pipeline (no classes/OOP).

Modules:
- chunk: split source into JSONL chunks
- index: embed chunks and build FAISS index
- generate: retrieve + prompt LLM + save tests
- evaluate: compute RAGAS context_precision

Expose CLIs through module-level main() plus __main__ guard.
"""

__all__ = []

