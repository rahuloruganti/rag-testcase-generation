from __future__ import annotations

import pickle
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from langchain_huggingface import HuggingFaceEmbeddings
import faiss
import numpy as np

try:  # optional import, loaded when available
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None

from .config import get_config

import re


def _sanitize_generated_tests(text: str) -> str:
    """Clean LLM output to be a valid pytest module.

    - Remove Markdown code fences
    - Sanitize function names (test_* only) to ASCII identifiers
    """
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw
        if line.strip().startswith("```"):
            continue
        if line.lstrip().startswith("def "):
            try:
                prefix_idx = line.index("def ") + 4
                paren_idx = line.index("(", prefix_idx)
                name = line[prefix_idx:paren_idx]
                if name.startswith("test_"):
                    safe = re.sub(r"[^0-9a-zA-Z_]", "_", name)
                    safe = re.sub(r"_+", "_", safe)
                    line = line[:prefix_idx] + safe + line[paren_idx:]
            except ValueError:
                pass
        lines.append(line)
    return "\n".join(lines)


def _load_faiss_artifacts(cfg: Dict[str, Any]) -> Tuple[faiss.Index, List[str], List[dict]]:
    if not cfg["faiss_index_path"].exists():
        raise FileNotFoundError("FAISS index not found. Run the index step first.")
    if not cfg["faiss_data_path"].exists():
        raise FileNotFoundError("FAISS metadata not found. Run the index step first.")

    index = faiss.read_index(str(cfg["faiss_index_path"]))
    with cfg["faiss_data_path"].open("rb") as f:
        data = pickle.load(f)

    documents: List[str] = data.get("documents", [])
    metadatas: List[dict] = data.get("metadatas", [])
    if len(documents) != len(metadatas):
        raise RuntimeError("FAISS metadata corrupt: documents and metadata length mismatch.")
    return index, documents, metadatas


def _retrieve_context(cfg: Dict[str, Any], question: str, k: int = 3) -> List[str]:
    index, documents, _ = _load_faiss_artifacts(cfg)
    if not documents:
        return []

    embeddings = HuggingFaceEmbeddings(model_name=cfg["embedding_model"])  # type: ignore
    query_vector = embeddings.embed_query(question)
    search_vector = np.asarray([query_vector], dtype="float32")
    k = min(k, len(documents))
    _, indices = index.search(search_vector, k)
    hits = [idx for idx in indices[0] if idx != -1]
    return [documents[idx] for idx in hits]


def _build_prompt(context: List[str], question: str) -> str:
    joined = "\n\n".join(context)
    prompt = f"""# Test Case Generation Task

You are an expert test automation engineer. I need you to generate new pytest test cases for Gmail login functionality.

## Reference Examples
Here are existing test cases from my Gmail test suite to use as templates:
{joined}

## Task: Generate New Test Cases
Based on my question: **{question}**

Please generate new pytest test case(s) following the EXACT same pattern as the reference examples above.

## Requirements:
1. Follow the exact naming convention: `def test_login_[scenario]_[number starting from 1](requests_mock):`
2. Use the same structure:
   - Set URL: `url = "https://accounts.google.com/v3/signin/verify"`
   - Create payload with email/password
   - Mock the response: `requests_mock.post(url, status_code=XXX)`
   - Make request: `resp = requests.post(url, json=payload)`
   - Assert status code: `assert resp.status_code == XXX`
3. Use realistic test data (emails, passwords, etc.)
4. Cover different scenarios related to my question

## Output Format:
Provide only the Python code for the new test functions, ready to paste into a pytest file.
"""
    return prompt


def _save_trace(
    cfg: Dict[str, Any],
    question: str,
    contexts: List[str],
    answer_text: str,
    prompt: str,
    k: int,
) -> Path:
    trace_dir = cfg["eval_traces_dir"]
    trace_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_path = trace_dir / f"trace_{ts}.jsonl"

    record = {
        "id": ts,
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "k": k,
        "contexts": contexts,
        "answer": answer_text,
        "model": cfg["openrouter_model"],
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "config": {
            "chunk_size": cfg["chunk_size"],
            "chunk_overlap": cfg["chunk_overlap"],
            "embedding_model": cfg["embedding_model"],
        },
    }
    with trace_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return trace_path


def generate(cfg: Dict[str, Any], question: str, k: int = 3) -> str:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Please install requirements.")

    ctx = _retrieve_context(cfg, question, k=k)
    prompt = _build_prompt(ctx, question)

    if not cfg.get("openrouter_api_key"):
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env.")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=cfg["openrouter_api_key"])  # type: ignore
    response = client.chat.completions.create(
        model=cfg["openrouter_model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=cfg["llm_max_tokens"],
        temperature=cfg["llm_temperature"],
    )

    if cfg.get("debug"):
        print(f"Response object: {response}")
        print(f"Response choices: {getattr(response, 'choices', None)}")

    if not response.choices:
        raise RuntimeError(f"No choices in OpenRouter response: {response}")

    answer_text = response.choices[0].message.content or ""
    answer_text = _sanitize_generated_tests(answer_text)
    _save_trace(cfg=cfg, question=question, contexts=ctx, answer_text=answer_text, prompt=prompt, k=k)
    return answer_text


def main(question: str = "testcase for blank password validation", k: int = 3) -> None:
    cfg = get_config()
    out_text = generate(cfg=cfg, question=question, k=k)
    out_dir = cfg["data_dir"] / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"testcases_{ts}.py"
    out_path.write_text(out_text, encoding="utf-8")
    print(f"🧠 Generated tests saved to: {out_path}")
    print("\nPreview:\n" + "-" * 40)
    print(out_text[:2000])

