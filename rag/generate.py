from __future__ import annotations

import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from pipeline.config import get_config, Config


def generate(cfg: Config, query: str) -> str:
    """
    Retrieve relevant chunks and generate a response using Gemini 1.5 Flash.
    """
    # 1. Load Vector Store
    index_path = getattr(cfg, "index_path", Path("data/index"))
    if isinstance(index_path, Path):
        load_path = str(index_path)
    else:
        load_path = str(index_path)

    if not os.path.exists(load_path):
        raise FileNotFoundError(f"Index not found at {load_path}. Run embedding step first.")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 2. Setup LLM (Gemini 1.5 Flash)
    # Ensure GOOGLE_API_KEY is set in environment
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # 3. Define Prompt
    template = """Answer the question based only on the following context:

{context}

Question: {question}
"""
    prompt = ChatPromptTemplate.from_template(template)

    # 4. Build Chain
    def format_docs(docs):
        return "\n\n".join([d.page_content for d in docs])

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 5. Execute
    print(f"❓ Query: {query}")
    response = chain.invoke(query)
    
    if cfg.debug:
        print(f"💡 Response:\n{response}")
        
    return response


def main() -> None:
    cfg = get_config()
    # Example query, in a real pipeline this might come from args or config
    test_query = "What are the key test cases for this code?"
    generate(cfg, test_query)


if __name__ == "__main__":
    main()
