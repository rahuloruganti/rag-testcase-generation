from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional at import time
    load_dotenv = None  # lazy fallback if not installed yet


@dataclass
class Config:
    # Inputs
    source_file: Path

    # Data dirs
    data_dir: Path
    faiss_dir: Path
    chunks_dir: Path
    # Evaluation dirs
    eval_dir: Path
    eval_traces_dir: Path
    eval_reports_dir: Path

    # Chunking
    chunk_language: str
    chunk_size: int
    chunk_overlap: int

    # Vector store
    embedding_model: str

    # LLM
    openrouter_api_key: Optional[str]
    openrouter_model: str
    llm_temperature: float
    llm_max_tokens: int

    # Diagnostics
    debug: bool

    # Derived files
    chunks_jsonl: Path
    faiss_index_path: Path
    faiss_data_path: Path


def _ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def get_config(env_path: Optional[Path] = None) -> Config:
    # Load .env once
    if load_dotenv is not None:
        if env_path is None:
            # Load both .env and .env.example to pick up defaults
            load_dotenv(override=False)
            example = Path(".env.example")
            if example.exists():
                load_dotenv(dotenv_path=example, override=False)
        else:
            load_dotenv(dotenv_path=str(env_path), override=False)

    # Base paths
    # Use top-level data/ dir by default (rag/ removed)
    data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
    faiss_dir = Path(os.getenv("FAISS_DIR", str(data_dir / "faiss"))).resolve()
    chunks_dir = Path(os.getenv("CHUNKS_DIR", str(data_dir / "chunks"))).resolve()
    eval_dir = Path(os.getenv("EVAL_DIR", str(data_dir / "eval"))).resolve()
    eval_traces_dir = eval_dir / "traces"
    eval_reports_dir = eval_dir / "reports"

    # Inputs
    source_file = Path(os.getenv("SOURCE_FILE", "docs/gmail_pytest_suite.py")).resolve()

    # Chunking
    chunk_language = os.getenv("CHUNK_LANGUAGE", "python").lower()
    chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Vector store
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # LLM
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-nano-9b-v2:free")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))

    # Diagnostics
    debug = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}

    # Derived files
    chunks_jsonl = chunks_dir / "chunks.jsonl"
    faiss_index_path = faiss_dir / "language_chunks_index.faiss"
    faiss_data_path = faiss_dir / "language_chunks_data.pkl"

    # Ensure dirs exist
    _ensure_dirs(data_dir, faiss_dir, chunks_dir, eval_dir, eval_traces_dir, eval_reports_dir)

    return Config(
        source_file=source_file,
        data_dir=data_dir,
        faiss_dir=faiss_dir,
        chunks_dir=chunks_dir,
        eval_dir=eval_dir,
        eval_traces_dir=eval_traces_dir,
        eval_reports_dir=eval_reports_dir,
        chunk_language=chunk_language,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        openrouter_api_key=openrouter_api_key,
        openrouter_model=openrouter_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
        debug=debug,
        chunks_jsonl=chunks_jsonl,
        faiss_index_path=faiss_index_path,
        faiss_data_path=faiss_data_path,
    )
