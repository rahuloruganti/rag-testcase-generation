from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Any

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings
import faiss

from .config import get_config


def _read_chunks_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            records.append(obj)
    return records


def index(cfg: Dict[str, Any]) -> Tuple[int, Path]:
    """Build a FAISS index from chunked JSONL and persist artifacts."""
    chunks_path = cfg["chunks_jsonl"]
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}. Run chunk step first.")

    records = _read_chunks_jsonl(chunks_path)
    texts = [r["text"] for r in records]
    metadatas = [r.get("metadata", {}) for r in records]

    embeddings = HuggingFaceEmbeddings(model_name=cfg["embedding_model"])  # type: ignore

    document_embeddings = embeddings.embed_documents(texts)
    embeddings_array = np.asarray(document_embeddings, dtype="float32")
    dim = embeddings_array.shape[1]
    faiss_index = faiss.IndexFlatL2(dim)
    faiss_index.add(embeddings_array)

    # Persist FAISS artifacts
    faiss.write_index(faiss_index, str(cfg["faiss_index_path"]))

    faiss_data = {
        "documents": texts,
        "metadatas": metadatas,
        "ids": [r["id"] for r in records],
        "chunking_method": "language_aware",
    }
    with cfg["faiss_data_path"].open("wb") as f:
        pickle.dump(faiss_data, f)

    if cfg.get("debug"):
        print(
            "Index: Read",
            chunks_path,
            "→ Wrote",
            cfg["faiss_index_path"],
            cfg["faiss_data_path"],
        )

    return len(texts), cfg["faiss_index_path"]


def main() -> None:
    cfg = get_config()
    n, faiss_path = index(cfg)
    print(f"✅ Indexed {n} chunks")
    print(f"💾 FAISS index: {faiss_path}")
