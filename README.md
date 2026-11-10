# rag-testcase-generation

An experiment in using retrieval-augmented generation to draft pytest cases. The pipeline chunks a Gmail login test suite, embeds the chunks with a sentence transformer, stores them in a FAISS index, retrieves the closest chunks for a question, and asks an LLM to write another test from that context. DVC runs the four stages in order.

The stages are wired end to end, but no generated suites or evaluation reports are checked in. There are therefore no published scores or baseline table.

## Setup

```bash
git clone https://github.com/rahuloruganti/rag-testcase-generation.git
cd rag-testcase-generation
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in two keys in `.env`: `GOOGLE_API_KEY` for the generator in `rag/generate.py` (Google Gemini) and `OPENROUTER_API_KEY` for the RAGAS judge. The chunk and index stages need neither.

Defaults come from `.env.example` and `pipeline/config.py`: the source is `docs/gmail_pytest_suite.py`, chunks are 500 characters with 50 overlap, embeddings use `sentence-transformers/all-MiniLM-L6-v2`, and generation asks `GEN_QUESTION` with `GEN_K=3` retrieved chunks.

`langchain-community` is held below 0.4.2 because RAGAS imports a module that release removed.

## Layout

- `rag/chunk.py`: splits the source file with a Python-aware character splitter and writes `data/chunks/chunks.jsonl`.
- `rag/embedding.py`: embeds those chunks and saves a FAISS index under `data/faiss/`.
- `rag/generate.py`: loads that index, retrieves context, calls Gemini, and saves the answer and a trace.
- `rag/evaluate.py`: scores a saved trace with RAGAS.
- `pipeline/config.py`: the configuration loader every `rag` module imports.
- `docs/gmail_pytest_suite.py`: 150 `requests-mock` login tests, not calls to a live Gmail account.
- `docs/gmail_test_cases.md`: the written reference cases.
- `tests/test_pipeline.py`: runs the four stages against a temporary directory with the embedding model and the LLM faked.
- `data/`: chunks, index, generated answers, traces, and reports. Git-ignored.

## Running the pipeline

```bash
dvc repro            # all four stages
dvc repro index      # chunk and index only, no API key needed
```

Each stage is also a module: `python -m rag.chunk`, `python -m rag.embedding`, `python -m rag.generate`, `python -m rag.evaluate --latest`.

| Stage | Reads | Writes |
|---|---|---|
| chunk | `docs/gmail_pytest_suite.py` | `data/chunks/chunks.jsonl` |
| index | `data/chunks/chunks.jsonl` | `data/faiss/language_chunks_index.faiss` and `.pkl` |
| generate | the index, `GEN_QUESTION`, `GEN_K` | `data/generated/generated_<time>.md`, `data/eval/traces/trace_<time>.jsonl` |
| evaluate | the newest trace | `data/eval/reports/report_context_precision.json` |

The index stage downloads the `all-MiniLM-L6-v2` weights on first use.

What has been run: `dvc repro index` completes on Windows with Python 3.13 and produces 150 chunks and the two index files. `dvc repro generate` reaches the Gemini call and stops there without a key. The generate and evaluate stages have not been run against the real Gemini and OpenRouter services; the test suite covers their file handling with a fake model.

## Evaluation

The only metric is RAGAS `context_precision`. It asks an LLM judge whether each retrieved chunk was relevant to the question and rewards relevant chunks that rank above irrelevant ones. A score near 1 means the retrieved set was mostly relevant and well ordered; it says nothing about whether retrieved code is correct.

Two limits matter here. The evaluation uses one trace with one question, and the code sets `reference` to the generated answer because there is no gold reference, so the judgement depends on the same model output being assessed. It measures retrieval quality, not whether a generated pytest file compiles, passes, or tests the intended behaviour. No metrics report is checked in, so there are no committed numbers for a metrics reader to display.

A trace is one JSON line with `question`, `contexts`, and `answer`.

## Testing

- Pipeline wiring: `pytest tests`
- Reference suite: `pytest docs/gmail_pytest_suite.py`
- Evaluation of the newest trace: `python -m rag.evaluate --latest` (or `--trace <path>`)

No measured baseline or before/after comparison is published, because no run output is part of the repository.
