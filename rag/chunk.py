from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

from .config import get_config


_LANG_MAP = {
    "python": Language.PYTHON,
    "md": Language.MARKDOWN,
    "markdown": Language.MARKDOWN,
    "js": Language.JS,
    "java": Language.JAVA,
}


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def chunk(cfg: Dict[str, Any]) -> Tuple[List[str], Path]:
    """Split the source file into language-aware chunks and write JSONL.

    Returns the list of chunk texts and the output JSONL path.
    """
    src = cfg["source_file"]
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    raw = _read_text_file(src)

    lang = _LANG_MAP.get(cfg["chunk_language"].lower(), Language.PYTHON)
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=lang,
        chunk_size=cfg["chunk_size"],
        chunk_overlap=cfg["chunk_overlap"],
    )

    chunks = splitter.split_text(raw)

    # Persist to JSONL
    out_path = cfg["chunks_jsonl"]
    with out_path.open("w", encoding="utf-8") as f:
        for i, text in enumerate(chunks):
            rec = {
                "id": f"chunk_{i}",
                "text": text,
                "metadata": {
                    "chunk_id": i,
                    "chunk_size": len(text),
                    "chunking_method": "language_aware",
                    "source": str(src.name),
                    "chunk_type": cfg["chunk_language"],
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if cfg.get("debug"):
        print(f"Chunk: Read {src} → Wrote {out_path}")

    return chunks, out_path


def main() -> None:
    cfg = get_config()
    chunks, path = chunk(cfg)
    print(f"🧩 Chunks created: {len(chunks)}")
    print(f"💾 Saved chunks to: {path}")
    if chunks:
        print("🔎 First chunk preview:\n" + chunks[0][:250])
