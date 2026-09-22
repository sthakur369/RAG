def get_existing_chunk_hashes(collection, source_name: str) -> dict:
    """
    Fetches existing chunks for a specific file/website from ChromaDB.
    Returns a dictionary mapping {chunk_hash: chunk_id}.
    """
    results = collection.get(
        where={"source": source_name},
        include=["metadatas"]
    )
    
    hash_to_id = {}
    if results and "ids" in results and "metadatas" in results:
        for chunk_id, meta in zip(results["ids"], results["metadatas"]):
            if "chunk_hash" in meta:
                hash_to_id[meta["chunk_hash"]] = chunk_id
                
    return hash_to_id

def delete_chunks_by_ids(collection, ids_to_delete: list[str]):
    """Surgically removes outdated chunks from ChromaDB."""
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"      [-] Deleted {len(ids_to_delete)} outdated chunks from DB.")

def purge_source_from_db(collection, source_name: str):
    """Used when a file is completely deleted from the raw_files folder."""
    collection.delete(where={"source": source_name})
    print(f"      [x] Purged all chunks for deleted source: {source_name}")