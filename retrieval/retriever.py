from embeddings.embedder import embed_query
from vector_db.chroma_db import search
from config.config import (
    QUESTION, 
    TOP_K, 
    CHUNKING_STRATEGY
    )


def retrieve(model):
    query_embedding = embed_query(model, QUESTION)

    results = search(
        query_embedding,
        TOP_K,
        CHUNKING_STRATEGY
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Stitch the text and metadata back together into a dictionary!
    retrieved_docs = []
    for doc, meta in zip(documents, metadatas):
        retrieved_docs.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "chunk_id": meta.get("chunk_id", "N/A"),
            "chunk_hash": meta.get("chunk_hash", "")
        })

    return (
        retrieved_docs,  # Now returning a list of DICTIONARIES
        metadatas,       # Keeping this here in case your main.py unpacking expects 3 items
        distances
    )