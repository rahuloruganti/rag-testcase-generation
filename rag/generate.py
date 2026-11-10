from __future__ import annotations

import json
from datetime import datetime

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from pipeline.config import get_config, Config

TEMPLATE = """Answer the question based only on the following context:

{context}

Question: {question}
"""


def generate(cfg: Config, query: str, k: int = 3) -> tuple[str, list[str]]:
    """Retrieve the k closest chunks and ask Gemini; returns the answer and the chunks it was given."""
    if not cfg.faiss_index_path.exists():
        raise FileNotFoundError(f"Index not found at {cfg.faiss_index_path}. Run the index stage first.")

    embeddings = HuggingFaceEmbeddings(model_name=cfg.embedding_model)
    # The pickle is the docstore this pipeline's own index stage wrote; LangChain refuses to load it without the flag.
    vectorstore = FAISS.load_local(
        str(cfg.faiss_dir),
        embeddings,
        index_name=cfg.faiss_index_path.stem,
        allow_dangerous_deserialization=True,
    )
    contexts = [doc.page_content for doc in vectorstore.as_retriever(search_kwargs={"k": k}).invoke(query)]

    # Reads GOOGLE_API_KEY from the environment.
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    chain = ChatPromptTemplate.from_template(TEMPLATE) | llm | StrOutputParser()

    print(f"❓ Query: {query}")
    response = chain.invoke({"context": "\n\n".join(contexts), "question": query})

    if cfg.debug:
        print(f"💡 Response:\n{response}")

    return response, contexts


def main() -> None:
    cfg = get_config()
    answer, contexts = generate(cfg, cfg.gen_question, cfg.gen_k)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = cfg.generated_dir / f"generated_{stamp}.md"
    out_path.write_text(answer, encoding="utf-8")
    trace_path = cfg.eval_traces_dir / f"trace_{stamp}.jsonl"
    trace = {"question": cfg.gen_question, "contexts": contexts, "answer": answer}
    trace_path.write_text(json.dumps(trace, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"💾 Saved answer: {out_path}")
    print(f"💾 Saved trace: {trace_path}")


if __name__ == "__main__":
    main()
