from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

from pipeline.config import get_config, Config


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunk(cfg: Config) -> List[Dict[str, Any]]:
    """Split the source file into language-aware chunks.

    Returns a list of dictionaries with chunk ID and text.
    """
    src = cfg.source_file
    
    raw = _read_text_file(src)

    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )

    texts = splitter.split_text(raw)

    chunks = []
    for i, text in enumerate(texts):
        chunks.append(
            {
                "id": f"chunk_{i}",
                "text": text,
            }
        )

    return chunks


def main() -> None:
    cfg = get_config()
    chunks = chunk(cfg)
    print(f"🧩 Chunks created: {len(chunks)}")


if __name__ == "__main__":
    main()
