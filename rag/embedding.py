from __future__ import annotations

from typing import List, Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from pipeline.config import get_config, Config
from rag.chunk import chunk


def embed(cfg: Config) -> None:
    """
    Generates embeddings for chunks and saves them to a FAISS index.
    """
    # 1. Get chunks
    chunks: List[Dict[str, Any]] = chunk(cfg)
    if not chunks:
        print("⚠️ No chunks found to embed.")
        return

    print(f"embedding: Processing {len(chunks)} chunks...")

    # 2. Convert to LangChain Documents
    documents = [
        Document(page_content=c["text"], metadata={"id": c["id"]})
        for c in chunks
    ]

    # 3. Initialize Embedding Model
    embeddings = HuggingFaceEmbeddings(model_name=cfg.embedding_model)

    # 4. Create Vector Store
    vectorstore = FAISS.from_documents(documents, embeddings)

    # 5. Save Index
    # FAISS save_local saves to a folder with an index name
    # We use the stem of the configured index path (e.g. "language_chunks_index")
    index_name = cfg.faiss_index_path.stem
    vectorstore.save_local(str(cfg.faiss_dir), index_name=index_name)
    
    print(f"✅ Index saved to {cfg.faiss_dir}/{index_name}")


def main() -> None:
    cfg = get_config()
    embed(cfg)


if __name__ == "__main__":
    main()
