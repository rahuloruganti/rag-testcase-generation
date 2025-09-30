from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from datasets import Dataset
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper

from ragas import evaluate as ragas_evaluate
from ragas.metrics import context_precision

from .config import get_config


def _load_trace(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        line = f.readline()
        obj = json.loads(line)
    return {
        "question": obj.get("question", ""),
        "contexts": obj.get("contexts", []) or [],
        "answer": obj.get("answer", ""),
    }


def _resolve_trace_path(cfg: Dict[str, Any], latest: bool, trace: Optional[str]) -> Path:
    if trace:
        return Path(trace).resolve()
    if latest:
        candidates = sorted(glob.glob(str(cfg["eval_traces_dir"] / "trace_*.jsonl")), reverse=True)
        if not candidates:
            raise FileNotFoundError(
                f"No traces found under {cfg['eval_traces_dir']}. Run generate first."
            )
        return Path(candidates[0]).resolve()
    raise ValueError("Provide --trace path or use --latest")


def run_context_precision_eval(cfg: Dict[str, Any], trace_path: Path) -> Tuple[float, Path]:
    rec = _load_trace(trace_path)

    ds = Dataset.from_dict(
        {
            "question": [rec["question"]],
            "contexts": [rec["contexts"]],
            "answer": [rec["answer"]],
            # No gold references; proxy with answer for metric compatibility
            "reference": [rec["answer"]],
        }
    )

    embeddings = HuggingFaceEmbeddings(model_name=cfg["embedding_model"])  # type: ignore

    if not cfg.get("openrouter_api_key"):
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env for evaluation.")

    chat = ChatOpenAI(
        model=cfg["openrouter_model"],
        api_key=cfg["openrouter_api_key"],
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
        max_retries=2,
    )
    llm = LangchainLLMWrapper(chat)

    column_map = {
        "user_input": "question",
        "retrieved_contexts": "contexts",
        "reference": "reference",
    }

    result = ragas_evaluate(ds, metrics=[context_precision], llm=llm, embeddings=embeddings, column_map=column_map)

    # Extract score robustly
    score: float
    try:
        if hasattr(result, "to_pandas"):
            df = result.to_pandas()  # type: ignore[attr-defined]
            score = float(df["context_precision"].iloc[0])
        elif isinstance(result, dict) and "context_precision" in result:
            score = float(result["context_precision"])  # type: ignore[index]
        else:
            score = float(result["context_precision"][0])  # type: ignore[index]
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Failed to parse ragas result: {e}")

    report_dir = cfg["eval_reports_dir"]
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "report_context_precision.json"
    payload = {
        "trace": str(trace_path),
        "metrics": {"context_precision": score},
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return score, out_path


def evaluate(cfg: Dict[str, Any], trace: Optional[str] = None, latest: bool = False) -> Tuple[float, Path]:
    path = _resolve_trace_path(cfg, latest=latest, trace=trace)
    return run_context_precision_eval(cfg, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG outputs with RAGAS")
    parser.add_argument("--trace", type=str, help="Path to a trace .jsonl file")
    parser.add_argument("--latest", action="store_true", help="Use the most recent trace")
    args = parser.parse_args()

    cfg = get_config()
    score, out = evaluate(cfg, trace=args.trace, latest=args.latest)
    print(f"📊 context_precision: {score:.4f}")
    print(f"💾 Saved report: {out}")
