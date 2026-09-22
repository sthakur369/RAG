import os
from ingestion.pdf_reader import read_single_pdf
from chunking.langchain_chunker import chunk_by_section_langchain
from embeddings.embedder import embed_documents

from data_sync.shared.normalizer import get_text_hash, generate_chunk_id
from data_sync.shared.db_sync import get_existing_chunk_hashes, delete_chunks_by_ids

def process_file_update(filename: str, raw_path: str, md_dir: str, collection, model):
    """
    Processes a single new or modified PDF:
    1. Extracts text and saves markdown.
    2. Chunks the text in memory.
    3. Hashes each chunk.
    4. Compares with existing hashes in ChromaDB.
    5. Deletes outdated chunks and embeds only new ones.
    """
    print(f"    -> Processing single file: {filename}")

    # 1. Read and convert this specific PDF to Markdown
    doc = read_single_pdf(raw_path, md_output_dir=md_dir)
    if not doc:
        print(f"      [SKIP] Skipping update for {filename} due to extraction error.")
        return

    # 2. Chunk only this document
    # chunk_by_section_langchain expects a list of documents
    raw_chunks = chunk_by_section_langchain([doc])
    
    if not raw_chunks:
        print(f"      [WARNING] No chunks generated for {filename}.")
        return

    # 3. Create deterministic Chunk IDs and hash map
    # Handles both LangChain Document objects and raw strings/dicts
    new_chunks_data = {}  # {chunk_hash: (chunk_id, chunk_text)}
    for index, chunk in enumerate(raw_chunks):
        chunk_text = chunk.page_content if hasattr(chunk, "page_content") else (chunk.get("text", "") if isinstance(chunk, dict) else str(chunk))
        
        c_hash = get_text_hash(chunk_text)
        c_id = generate_chunk_id(filename, index, c_hash)
        new_chunks_data[c_hash] = (c_id, chunk_text)

    # 4. Compare with existing chunk hashes in ChromaDB
    old_hash_to_id = get_existing_chunk_hashes(collection, filename)
    old_hashes = set(old_hash_to_id.keys())
    new_hashes = set(new_chunks_data.keys())

    hashes_to_delete = old_hashes - new_hashes
    hashes_to_add = new_hashes - old_hashes

    # 5. Surgical delete of outdated chunks
    if hashes_to_delete:
        ids_to_delete = [old_hash_to_id[h] for h in hashes_to_delete]
        delete_chunks_by_ids(collection, ids_to_delete)

    # 6. Embed & Add Mismatched New Chunks
    if hashes_to_add:
        raw_text_chunks = [new_chunks_data[h][1] for h in hashes_to_add]
        ids_to_add = [new_chunks_data[h][0] for h in hashes_to_add]
        metadatas = [
            {"source": filename, "chunk_hash": h, "doc_type": "pdf"}
            for h in hashes_to_add
        ]

        print(f"      [+] Embedding and inserting {len(hashes_to_add)} chunk(s)...")

        # FIX: Wrap raw strings into {"text": text} dicts for embed_documents
        payload_for_embedder = [{"text": t} for t in raw_text_chunks]
        new_embeddings = embed_documents(model, payload_for_embedder)

        # ChromaDB accepts raw_text_chunks directly
        collection.add(
            documents=raw_text_chunks,
            embeddings=new_embeddings,
            metadatas=metadatas,
            ids=ids_to_add
        )
        
    else:
        print("      [=] Content unchanged. No new embeddings generated.")