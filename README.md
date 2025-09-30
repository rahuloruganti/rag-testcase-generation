# rag-testcase-generation

Simple RAG pipeline to chunk a Gmail pytest suite, build a FAISS index, and generate new pytest cases via an LLM (OpenRouter). The workflow is orchestrated by DVC.

## Quick Start

- Install deps: `pip install -r requirements.txt`
- Configure env: copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` (optionally set `GEN_QUESTION`, `GEN_K`)
- Run all steps: `dvc repro`

## Project Layout

- `rag/`: procedural modules (`chunk`, `index`, `generate`, `evaluate`, `config`).
- `docs/`: Gmail pytest reference suite and project docs.
- `data/`: generated artifacts (chunks, FAISS index, generated tests). Git-ignored.

Beginner Guide: `docs/BEGINNER_GUIDE.md`

## Commands (DVC)

- `dvc repro` — runs chunk → index → generate → evaluate
- `dvc repro chunk|index|generate|evaluate` — run a specific stage
- `dvc metrics show` — display evaluation metrics

## Env Config

- `SOURCE_FILE`: path to source file (default `docs/gmail_pytest_suite.py`).
- `DATA_DIR`: base data dir (default `data`).
- `FAISS_DIR` / `CHUNKS_DIR`: output dirs for the FAISS index and chunk artifacts.
- `CHUNK_LANGUAGE` / `CHUNK_SIZE` / `CHUNK_OVERLAP`: chunking params.
- `EMBEDDING_MODEL`: HF sentence transformer.
- `OPENROUTER_API_KEY`: your OpenRouter API key.
- `OPENROUTER_MODEL`: model slug (default `nvidia/nemotron-nano-9b-v2:free`).
- `LLM_TEMPERATURE` / `LLM_MAX_TOKENS`: generation params.

Generated tests are saved under `data/generated/`.

## Testing

- Baseline regression: `pytest docs/gmail_pytest_suite.py`
- Validate generated suites: `pytest data/generated/testcases_*.py` (after running generate)

## Evaluation

- We provide an evaluation using RAGAS `context_precision`.
- Generation writes an evaluation trace to `data/eval/traces/trace_*.jsonl`.
- DVC runs evaluation in the `evaluate` stage, writing a report to `data/eval/reports/report_context_precision.json`.

Reports are saved under `data/eval/reports/` as JSON.

## Notes

- The old `pipeline/` folder has been removed. Use DVC stages with the modules under `rag/`.
- Ensure the embedding model is available locally or internet access is enabled for first run.
 - For evaluation, we use `ragas` with the configured embedding model.
