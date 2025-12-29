from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from pipeline.config import get_config, Config
from rag.chunk import chunk


def embed(cfg: Config) -> None:
    """
    Convert chunks to vectors and store in a FAISS vector database.
    """
    # 1. Generate chunks
    chunks_list = chunk(cfg)
    if not chunks_list:
        print("No chunks generated.")
        return

    texts = [c["text"] for c in chunks_list]
    metadatas = [{"id": c["id"]} for c in chunks_list]
 
    # 2. Initialize Embeddings
    # Using a standard efficient model
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 3. Create Vector Store
    print(f"Embedding {len(texts)} chunks...")
    vectorstore = FAISS.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas
    )

    # 4. Save Index
    # Default to data/index if not specified in config
    index_path = getattr(cfg, "index_path", Path("data/index"))
    
    # Ensure parent directory exists
    if isinstance(index_path, Path):
        index_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = str(index_path)
    else:
        save_path = str(index_path)

    vectorstore.save_local(save_path)
    print(f"💾 Index saved to: {save_path}")


def main() -> None:
    cfg = get_config()
    embed(cfg)


if __name__ == "__main__":
    main()
