import chromadb # type: ignore
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction # type: ignore

import os
from pypdf import PdfReader # type: ignore

from django.conf import settings

client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,
    port=8000,
)
embedding_fn = DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="coolbreeze_docs",
    embedding_function=embedding_fn
)


def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1

        if current_size >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_size = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def load_documents():
    docs_path = "support/documents/"

    documents = []
    ids = []
    metadatas = []

    for filename in os.listdir(docs_path):
        if filename.endswith(".pdf"):
            filepath = os.path.join(docs_path, filename)
            reader = PdfReader(filepath)

            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text()

            chunks = chunk_text(raw_text, chunk_size=500)

            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                ids.append(f"{filename}_{i}")
                metadatas.append({
                    "source_type": "internal_document",
                    "document": filename,
                    "chunk_index": i,
                })

    if documents:
        collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    print(f"Loaded {len(documents)} chunks into ChromaDB")


def search_knowledge_base(query):
    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas"],
    )

    matched_docs = results["documents"][0]
    matched_metas = results["metadatas"][0]

    if not matched_docs:
        return {
            "source": "internal_document",
            "results": [],
        }

    formatted_results = []
    for content, meta in zip(matched_docs, matched_metas):
        formatted_results.append({
            "document": meta.get("document", "unknown"),
            "content": content,
        })

    return {
        "source": "internal_document",
        "results": formatted_results,
    }