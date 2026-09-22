import chromadb # type: ignore
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction # type: ignore
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from support.models import DocumentChunk # type: ignore
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
    docs_path = os.path.join(settings.BASE_DIR, "support", "documents")

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
                DocumentChunk.objects.update_or_create(
                    document=filename,
                    chunk_index=i,
                    defaults={"content": chunk},
)

    if documents:
        collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    print(f"Loaded {len(documents)} chunks into ChromaDB")



    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas"],
    )

    matched_docs = results["documents"][0]
    matched_metas = results["metadatas"][0]



    formatted_results = []
    if not matched_docs:
        for content, meta in zip(matched_docs, matched_metas):
            formatted_results.append({
                "document": meta.get("document", "unknown"),
                "content": content,
            })

    return {
        "source": "internal_document",
        "results": formatted_results,
    }

def search_knowledge_base(query):
    vector_results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas"],
    )

    vector_matches = []
    if vector_results["documents"][0]:
        for content, meta in zip(vector_results["documents"][0], vector_results["metadatas"][0]):
            vector_matches.append({
                "document": meta.get("document", "unknown"),
                "content": content,
            })

    text_matches = full_text_search(query, limit=3)

    combined = {}

    for i, match in enumerate(vector_matches):
        key = match["document"] + "::" + match["content"][:50]
        combined[key] = {**match, "matched_by": {"vector"}, "vector_rank": i}

    for i, match in enumerate(text_matches):
        key = match["document"] + "::" + match["content"][:50]
        if key in combined:
            combined[key]["matched_by"].add("full_text")
            combined[key]["text_rank"] = i
        else:
            combined[key] = {**match, "matched_by": {"full_text"}, "text_rank": i}

    def sort_key(item):
        matched_both = len(item["matched_by"]) == 2
        best_rank = min(item.get("vector_rank", 99), item.get("text_rank", 99))
        return (0 if matched_both else 1, best_rank)

    ranked = sorted(combined.values(), key=sort_key)[:5]

    formatted_results = [
        {"document": r["document"], "content": r["content"]}
        for r in ranked
    ]

    if not formatted_results:
        return {"source": "internal_document", "results": []}

    return {"source": "internal_document", "results": formatted_results}


def full_text_search(query, limit=3):
    search_query = SearchQuery(query)
    results = (
        DocumentChunk.objects.annotate(
            rank=SearchRank(SearchVector("content"), search_query)
        )
        .filter(rank__gt=0)
        .order_by("-rank")[:limit]
    )
    return [
        {"document": r.document, "content": r.content}
        for r in results
    ]