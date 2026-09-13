import chromadb # type: ignore
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction # type: ignore

import os
from pypdf import PdfReader # type: ignore

import chromadb # type: ignore
from django.conf import settings

client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,   # از env، مقدارش "chromadb" هست طبق docker-compose
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

    for filename in os.listdir(docs_path):
        if filename.endswith(".pdf"):
            # filepath: support/documents/refund_policy.pdf
            filepath = os.path.join(docs_path, filename)
            reader = PdfReader(filepath)
            
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text()

            chunks = chunk_text(raw_text, chunk_size=500)

            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                ids.append(f"{filename}_{i}")

    if documents:
        collection.add(documents=documents, ids=ids)

    print(f"Loaded {len(documents)} chunks into ChromaDB")


def search_knowledge_base(query):
    results = collection.query(query_texts=[query], n_results=3)
    print("DEBUG RESULTS:", results["documents"])
    if not results["documents"][0]:
        return "No relevant information found in company documents."
    
    matched_chunks = results["documents"][0]
    return "\n\n".join(matched_chunks)