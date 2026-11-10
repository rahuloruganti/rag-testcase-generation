"""The four stages run in order against one data directory, with the model download and the LLM faked."""

from __future__ import annotations

import json

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import FakeListChatModel

from pipeline.config import get_config
from rag import chunk, embedding, evaluate, generate

ANSWER = "def test_blank_password(): ..."


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    for name in ("FAISS_DIR", "CHUNKS_DIR", "EVAL_DIR"):
        monkeypatch.setenv(name, str(tmp_path / name.split("_")[0].lower()))
    fake_embeddings = lambda model_name: DeterministicFakeEmbedding(size=32)  # noqa: E731
    monkeypatch.setattr(embedding, "HuggingFaceEmbeddings", fake_embeddings)
    monkeypatch.setattr(generate, "HuggingFaceEmbeddings", fake_embeddings)
    monkeypatch.setattr(generate, "ChatGoogleGenerativeAI", lambda **kwargs: FakeListChatModel(responses=[ANSWER]))
    return get_config()


def test_chunk_stage_writes_the_file_the_index_stage_reads(cfg):
    chunk.main()

    rows = [json.loads(line) for line in cfg.chunks_jsonl.read_text(encoding="utf-8").splitlines()]
    assert rows and rows[0]["id"] == "chunk_0" and rows[0]["text"]


def test_index_stage_writes_the_files_the_config_names(cfg):
    chunk.main()
    embedding.main()

    assert cfg.faiss_index_path.is_file()
    assert cfg.faiss_data_path.is_file()


def test_generate_reads_that_index_and_leaves_an_answer_and_a_trace(cfg):
    chunk.main()
    embedding.main()
    generate.main()

    answers = list(cfg.generated_dir.iterdir())
    assert len(answers) == 1 and answers[0].read_text(encoding="utf-8") == ANSWER
    traces = list(cfg.eval_traces_dir.glob("trace_*.jsonl"))
    assert len(traces) == 1
    trace = json.loads(traces[0].read_text(encoding="utf-8"))
    assert trace["question"] == cfg.gen_question
    assert trace["answer"] == ANSWER
    assert len(trace["contexts"]) == cfg.gen_k


def test_evaluate_finds_and_loads_the_trace_generate_wrote(cfg):
    chunk.main()
    embedding.main()
    generate.main()

    path = evaluate._resolve_trace_path(cfg, latest=True, trace=None)
    record = evaluate._load_trace(path)

    assert record["answer"] == ANSWER and len(record["contexts"]) == cfg.gen_k
