import chromadb

from config.config import (
    CHROMA_DB_PATH, 
    COLLECTION_NAME,
    CHUNKING_STRATEGY
    )

client = chromadb.PersistentClient(path = CHROMA_DB_PATH)


def get_all_chunks():
    collection = get_collection(CHUNKING_STRATEGY)
    results = collection.get(
        include=["documents", "metadatas"]
    )

    chunks = []

    for chunk_id, text, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"]
    ):
        chunk = {
            "chunk_id": chunk_id,
            "text": text,
            **(metadata or {})
        }

        chunks.append(chunk)

    return chunks

def get_chunks(source):
    collection = get_collection(CHUNKING_STRATEGY)

    result = collection.get(
        where={"source": source},
        include=["metadatas"]
    )

    return result["metadatas"]


def compare_chunks(old_chunks, new_chunks):
    old_hashes = {
        chunk["chunk_hash"]: chunk["chunk_id"]
        for chunk in old_chunks
    }

    new_hashes = {
        chunk["chunk_hash"]
        for chunk in new_chunks
    }

    chunks_to_add = []

    for chunk in new_chunks:
        if chunk["chunk_hash"] in old_hashes:
            print(f"Hash matched, ignoring: {chunk['chunk_id']}")
        else:
            chunks_to_add.append(chunk)

    chunk_ids_to_delete = [
        chunk_id
        for chunk_hash, chunk_id in old_hashes.items()
        if chunk_hash not in new_hashes
    ]

    return chunks_to_add, chunk_ids_to_delete


def delete_chunks(source, chunk_ids):
    collection = get_collection(CHUNKING_STRATEGY)

    for chunk_id in chunk_ids:
        result = collection.get(
            where={
                "$and": [
                    {"source": source},
                    {"chunk_id": chunk_id}
                ]
            },
            include=[]
        )

        if result["ids"]:
            collection.delete(ids=result["ids"])


def add_chunks(chunks, embeddings):
    collection = get_collection(CHUNKING_STRATEGY)

    collection.add(
        ids=[chunk["chunk_id"] for chunk in chunks],
        embeddings=embeddings.tolist(),
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[
            {
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "chunk_section": chunk["section"],
                "chunk_hash": chunk["chunk_hash"]
            }
            for chunk in chunks
        ]
    )





def get_collection(chunking_strategy):
    collection_name = f"{COLLECTION_NAME}_{chunking_strategy}"

    return client.get_or_create_collection(
        name = collection_name,
        configuration =
        {
            "hnsw": 
            {
                "space": "cosine"
            }
        }
    )


def add_documents(documents, embeddings):
    collection = get_collection(CHUNKING_STRATEGY)

    ids = [
        doc["chunk_id"] 
        for doc in documents
    ]

    collection.add(
        ids = ids,
        embeddings = embeddings.tolist(),
        documents = [doc["text"] for doc in documents],
        metadatas=[
            {
                "source": doc["source"],
                "chunk_id": doc["chunk_id"],
                "chunk_section": doc["section"],
                "chunk_hash": doc["chunk_hash"]

            }

            for doc in documents
        ]
    )


def search(query_embedding, top_k, chunking_strategy):
    collection = get_collection(chunking_strategy)

    return collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k
    )