# rag-testcase-generation

An experiment in using retrieval-augmented generation to draft pytest cases. The pipeline chunks a Gmail login test suite, embeds the chunks with a sentence transformer, stores them in a FAISS index, retrieves the closest chunks for a question, and asks an LLM to write another test from that context. DVC files describe the intended stages.

This README describes the repository at commit `7aca217`. The refactor is not finished: the DVC stage names and the Python modules do not fully agree, generation is not connected to the index that the embedding step writes, and no generated suites or evaluation reports are checked in. There are therefore no published scores or baseline table.

## Setup

```bash
git clone https://github.com/rahuloruganti/rag-testcase-generation.git
cd rag-testcase-generation
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`OPENROUTER_API_KEY` is used by the RAGAS judge. The generator in `rag/generate.py` currently uses Google Gemini and reads `GOOGLE_API_KEY`, which is not listed in `.env.example`. `requirements.txt` also omits `langchain-community` and `langchain-google-genai`, although both are imported.

Defaults come from `.env.example` and `pipeline/config.py`: the source is `docs/gmail_pytest_suite.py`, chunks are 500 characters with 50 overlap, embeddings use `sentence-transformers/all-MiniLM-L6-v2`, and generation retrieves `k=3`.

## Layout

- `rag/chunk.py`: splits the source file with a Python-aware character splitter.
- `rag/embedding.py`: embeds the chunks and saves a FAISS index.
- `rag/generate.py`: loads an index, retrieves context, and calls Gemini.
- `rag/evaluate.py`: scores a saved trace with RAGAS.
- `pipeline/config.py`: the active configuration loader. Every `rag` module imports from it, so the `pipeline/` directory has not been removed.
- `docs/gmail_pytest_suite.py`: 150 `requests-mock` login tests, not calls to a live Gmail account.
- `docs/gmail_test_cases.md`: the written reference cases.
- `data/`: chunks, index, generated tests, traces, and reports. Git-ignored.

## Pipeline status

The DVC definitions do not match the code at this commit:

- `dvc.yaml` calls `rag.config` and `rag.index`; the configuration lives in `pipeline/config.py` and indexing is implemented in `rag/embedding.py`, so `dvc repro` fails at the chunk stage.
- The embedding step writes `data/faiss/language_chunks_index.faiss` and `data/faiss/language_chunks_index.pkl`, not the names `dvc.yaml` declares. `embed()` calls `vectorstore.save_local(str(cfg.faiss_dir), index_name=cfg.faiss_index_path.stem)`, and LangChain's `FAISS.save_local` writes exactly two files, `<index_name>.faiss` and `<index_name>.pkl`. With the stem `language_chunks_index` that yields `language_chunks_index.faiss` and `language_chunks_index.pkl`. The `index` stage instead lists `language_chunks_data.pkl`, which comes from `Config.faiss_data_path` and which nothing writes, so the declared `data/faiss/*.pkl` output never appears.
- `rag/generate.py` looks for `data/index` because `Config` has no `index_path` attribute, and it calls `FAISS.load_local` without an `index_name`, so it would expect `data/index/index.faiss`. Generation is therefore not wired to the index the embedding step builds in `data/faiss`.
- Generation returns its answer to the caller, and `main()` discards it. Nothing writes `data/generated` or an evaluation trace. The `evaluate` stage needs a `data/eval/traces/trace_*.jsonl` file, and none is committed.

The chunker and index builder can be run directly:

```bash
python -c "from pipeline.config import get_config; from rag.chunk import chunk; print(len(chunk(get_config())))"
python -c "from pipeline.config import get_config; from rag.embedding import embed; embed(get_config())"
```

The chunk command downloads nothing: it only splits the source file with `langchain-text-splitters`, which `requirements.txt` lists. The embedding command downloads the `all-MiniLM-L6-v2` weights on first use, and it needs `langchain-community` for `FAISS`, which `requirements.txt` omits. `langchain-google-genai` is required only by `rag/generate.py`, not by either command above. Neither command was run for this README.

## Evaluation

The only metric is RAGAS `context_precision`. It asks an LLM judge whether each retrieved chunk was relevant to the question and rewards relevant chunks that rank above irrelevant ones. A score near 1 means the retrieved set was mostly relevant and well ordered; it says nothing about whether retrieved code is correct.

Two limits matter here. The evaluation uses one trace with one question, and the code sets `reference` to the generated answer because there is no gold reference, so the judgement depends on the same model output being assessed. It measures retrieval quality, not whether a generated pytest file compiles, passes, or tests the intended behaviour. The module also lacks imports at this commit. `json`, `glob`, `argparse`, and `pathlib.Path` are each used at runtime and never imported, so both `--latest` and `--trace` fail before scoring; other names such as `Dict`, `Any`, `Optional`, and `Tuple` appear only in annotations and are deferred by `from __future__ import annotations`, so this list should not be read as exhaustive. No metrics report is checked in, so there are no committed numbers for a metrics reader to display; DVC was not run for this README.

The expected trace fields are `question`, `contexts`, and `answer`. The scorer is intended to write `data/eval/reports/report_context_precision.json` once those import errors are fixed and a trace exists.

## Testing

- Reference suite: `pytest docs/gmail_pytest_suite.py`
- Generated suites, if produced, would go under `data/generated/`; the current generator does not create them.
- Evaluation: `python -m rag.evaluate --latest` (or `--trace <path>`) is the intended entry point, but it fails at this commit because the module is missing imports.

No measured baseline or before/after comparison is published, because no run output is part of the repository.
