"""
memory/vector_store.py

Semantic/vector search using ChromaDB. Local only: pyros_data/vector_db/
"""
import chromadb
from chromadb.utils import embedding_functions
import uuid
import hashlib

CHROMA_PATH = "pyros_data/vector_db"

_client = chromadb.PersistentClient(path=CHROMA_PATH)

_embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_documents_collection = _client.get_or_create_collection(
    name="documents", embedding_function=_embedder
)
_conversations_collection = _client.get_or_create_collection(
    name="conversations", embedding_function=_embedder
)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def add_document(text: str, source_file: str, extra_metadata: dict = None) -> int:
    chunks = chunk_text(text)
    added = 0
    for i, chunk in enumerate(chunks):
        chunk_hash = _hash_text(chunk)
        existing = _documents_collection.get(where={"chunk_hash": chunk_hash})
        if existing["ids"]:
            continue

        metadata = {"source_file": source_file, "chunk_index": i, "chunk_hash": chunk_hash}
        if extra_metadata:
            metadata.update(extra_metadata)
        _documents_collection.add(
            documents=[chunk],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())],
        )
        added += 1
    return added


def delete_document(source_file: str):
    _documents_collection.delete(where={"source_file": source_file})


def search_documents(query: str, top_k: int = 5, metadata_filter: dict = None) -> list:
    results = _documents_collection.query(
        query_texts=[query],
        n_results=top_k,
        where=metadata_filter,
    )
    return _format_results(results)


def add_conversation_memory(text: str, tag: str = "general"):
    _conversations_collection.add(
        documents=[text],
        metadatas=[{"tag": tag}],
        ids=[str(uuid.uuid4())],
    )


def search_conversation_memory(query: str, top_k: int = 5) -> list:
    results = _conversations_collection.query(query_texts=[query], n_results=top_k)
    return _format_results(results)


def re_rank(candidates: list, keep_top: int = 3) -> list:
    return sorted(candidates, key=lambda c: c["distance"])[:keep_top]


def collection_stats() -> dict:
    return {
        "document_chunks": _documents_collection.count(),
        "conversation_snippets": _conversations_collection.count(),
    }


def _format_results(raw_results) -> list:
    docs = raw_results.get("documents", [[]])[0]
    metas = raw_results.get("metadatas", [[]])[0]
    distances = raw_results.get("distances", [[]])[0]
    return [
        {"text": d, "metadata": m, "distance": dist}
        for d, m, dist in zip(docs, metas, distances)
    ]