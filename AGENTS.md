# Repository Guidelines

## Project Structure & Module Organization
- `rag/`: procedural RAG pipeline — `chunk.py`, `index.py`, `generate.py`, `evaluate.py`, `config.py`.
- `docs/`: Gmail pytest reference material that seeds retrieval prompts and project docs.
- `data/`: cache directory for FAISS artifacts, chunked inputs, and generated pytest suites.
- `requirements.txt`: single source for runtime dependencies.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: optional local virtualenv.
- `pip install -r requirements.txt`: install dependencies.
- DVC workflow (preferred):
  - `dvc repro` — run chunk → index → generate → evaluate
  - `dvc repro chunk|index|generate|evaluate` — run a specific stage
  - `dvc metrics show` — show evaluation metrics

## Coding Style & Naming Conventions
- Follow PEP 8, four-space indentation, and keep lines ≤ 100 characters.
- Type hint new public functions; config is a plain dict (see `rag/config.py`).
- Prefix module-private helpers with `_`; expose callable functions (no CLI entrypoints).
- Persist text as UTF-8 and write JSON with `ensure_ascii=False` to retain source characters.

## Testing Guidelines
- `pytest docs/gmail_pytest_suite.py`: baseline regression against the curated Gmail suite.
- `pytest data/generated/testcases_*.py`: validate that LLM output compiles and respects the mocked contract.
- Add unit tests under `tests/` (create if missing) using `test_<module>_<behavior>.py` naming.
- Seed any randomness and document external dependencies so retrieval stays reproducible.

## Commit & Pull Request Guidelines
- Keep commits focused and imperative (`Refine chunk splitter config`, `Add FAISS index smoke test`).
- Describe configuration or dependency changes in the body when they affect operators.
- Pull requests should summarize the change, list commands run, link issues, and attach representative generated snippets when relevant.
- Confirm `pytest` passes and clear untracked artifacts from `data/` before requesting review.

## Environment & Data Safety
- Copy `.env.example` to `.env`; provide `OPENROUTER_API_KEY`, chunking parameters, and storage paths before running the pipeline.
- Treat `data/` as cache: commit reproducible checkpoints deliberately, but never version secrets or large embeddings.
- Keep `.env` and `rag/config.py` aligned when rotating models or API keys.

```
<!-- FAST-TOOLS PROMPT v1 | codex-mastery | watermark:do-not-alter -->

## CRITICAL: Use ripgrep, not grep

NEVER use grep for project-wide searches (slow, ignores .gitignore). ALWAYS use rg.

- `rg "pattern"` — search content
- `rg --files | rg "name"` — find files
- `rg -t python "def"` — language filters

## File finding

- Prefer `fd` (or `fdfind` on Debian/Ubuntu). Respects .gitignore.

## JSON

- Use `jq` for parsing and transformations.

## Install Guidance

- macOS: `brew install ripgrep fd jq`
- Debian/Ubuntu: `sudo apt update && sudo apt install -y ripgrep fd-find jq` (alias `fd=fdfind`)

## Agent Instructions

- Replace commands: grep→rg, find→rg --files/fd, ls -R→rg --files, cat|grep→rg pattern file
- Cap reads at 250 lines; prefer `rg -n -A 3 -B 3` for context
- Use `jq` for JSON instead of regex

<!-- END FAST-TOOLS PROMPT v1 | codex-mastery -->
```
