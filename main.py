import time
import asyncio

# 
from data_sync.shared.state_manager import (
    add_entry,
    update_entry,
    delete_entry,
    get_last_modified,
    load_state,
    save_state
)

from config.config import (
     STATE_FILE_JSON,
     STATE_WEBSITE_JSON,
     QUESTION)

from data_sync.detection.detect_files import detect_file_changes

from ingestion.pdf_reader import read_pdfs
from ingestion.web_reader_langchain import read_websites_langchain_async

from chunking.langchain_chunker import chunk_by_section_langchain

from embeddings.embedder import load_model, embed_documents

from embeddings.hashing import generate_chunk_hash

from vector_db.chroma_db import add_documents, get_chunks, delete_chunks, add_chunks, compare_chunks, get_all_chunks

from retrieval.retriever import retrieve
from retrieval.bm25_search import retrieve_bm25

from reranker.reranker import load_reranker, rerank_documents

from generation.generator import generate_answer

from evaluation.evaluator import PipelineDiagnostics



async def main():
    # 1. INITIALIZE DIAGNOSTICS TRACKER
    diagnostics = PipelineDiagnostics()

    # start = time.perf_counter()
    pdf_docs = []

    print("\n" + "=" * 80)
    print("RAG PIPELINE")
    print("=" * 80)

    # Load models
    diagnostics.start("1. Load Embedding Model")
    model = load_model()
    diagnostics.stop("1. Load Embedding Model")

    diagnostics.start("2. Load Reranking Model")
    reranker = load_reranker()
    diagnostics.stop("2. Load Reranking Model")

    # Detect PDF changes
    diagnostics.start("3. Data Synchronization")  
    new_files, deleted_files, updated_files = detect_file_changes()

    print("new_files:", new_files)
    print("deleted_files:", deleted_files)
    print("updated_files:", updated_files)

    # ---------------------------------------------------------
    # NEW FILES
    # ---------------------------------------------------------
    for file in new_files:
        print("\n" + "=" * 80)
        print(f"\n[NEW] File: {file}")

        # Read PDF
        pdf_docs = read_pdfs([file])
        print(f"[NEW] PDF documents read: {len(pdf_docs)}")

        # Create chunks
        chunks = chunk_by_section_langchain(pdf_docs)
        print(f"[NEW] Chunks created: {len(chunks)}, {type(chunks)}")

        # Generate hashes
        for chunk in chunks:
            chunk["chunk_hash"] = generate_chunk_hash(chunk["text"])

        print(f"[NEW] Hashes generated: {len(chunks)}")

        # Create embeddings
        embeddings = embed_documents(model, chunks)
        print(f"[NEW] Embeddings created: {len(embeddings)}")

        # Add to ChromaDB
        add_chunks(chunks, embeddings)
        print(f"[NEW] Chunks added to ChromaDB: {len(chunks)}")

        # Add to state JSON
        add_entry(
            STATE_FILE_JSON,
            {
                "raw_file_name": file,
                "md_file_name": pdf_docs[0]["source"],
                "raw_file_last_modified_date": get_last_modified(
                    f"data/files/raw_files/{file}"
                ),
            },
        )

        print("[NEW] State JSON updated")
        print(f"[NEW] Completed: {file}")

    # ---------------------------------------------------------
    # UPDATED FILES
    # ---------------------------------------------------------
    for file in updated_files:
        print(f"\n[UPDATE] File: {file}")

        # Read PDF
        pdf_docs = read_pdfs([file])
        print(f"[UPDATE] PDF documents read: {len(pdf_docs)}")

        # Create chunks
        chunks = chunk_by_section_langchain(pdf_docs)
        print(f"[UPDATE] New chunks created: {len(chunks)}")

        # Generate hashes
        for chunk in chunks:
            chunk["chunk_hash"] = generate_chunk_hash(chunk["text"])

        print(f"[UPDATE] Hashes generated: {len(chunks)}")

        # Get source and old chunks
        source = pdf_docs[0]["source"]
        old_chunks = get_chunks(source)

        print(f"[UPDATE] Source: {source}")
        print(f"[UPDATE] Existing chunks: {len(old_chunks)}")

        # Compare old and new chunks
        chunks_to_add, chunk_ids_to_delete = compare_chunks(
            old_chunks,
            chunks
        )

        print(f"[UPDATE] Chunks to add: {len(chunks_to_add)}")
        print(f"[UPDATE] Chunks to delete: {len(chunk_ids_to_delete)}")

        # Delete old/changed chunks
        if chunk_ids_to_delete:
            delete_chunks(source, chunk_ids_to_delete)

            remaining_chunks = get_chunks(source)

            print(
                f"[UPDATE] Chunks remaining after delete: "
                f"{len(remaining_chunks)}"
            )

        else:
            print("[UPDATE] No chunks to delete")

        # Add new/changed chunks
        if chunks_to_add:
            embeddings = embed_documents(model, chunks_to_add)
            print(f"[UPDATE] Embeddings created: {len(embeddings)}")

            add_chunks(chunks_to_add, embeddings)
            print(f"[UPDATE] Chunks added to ChromaDB: {len(chunks_to_add)}")

        else:
            print("[UPDATE] No chunks to add")

        # Update state JSON
        update_entry(
            STATE_FILE_JSON,
            file,
            {
                "raw_file_last_modified_date": get_last_modified(
                    f"data/files/raw_files/{file}"
                )
            },
        )

        print("[UPDATE] State JSON updated")
        print(f"[UPDATE] Completed: {file}")

    # ---------------------------------------------------------
    # DELETED FILES
    # ---------------------------------------------------------
    if deleted_files:
        state = load_state(STATE_FILE_JSON)

        for file in deleted_files:
            for entry in state:
                if entry["raw_file_name"] == file:
                    source = entry["md_file_name"]
                    old_chunks = get_chunks(source)

                    print(f"\n[DELETE] File: {file}")
                    print(f"[DELETE] Source: {source}")
                    print(f"[DELETE] Chunks found: {len(old_chunks)}")

                    chunk_ids = [
                        chunk["chunk_id"]
                        for chunk in old_chunks
                    ]

                    if chunk_ids:
                        delete_chunks(source, chunk_ids)

                        remaining_chunks = get_chunks(source)

                        print(
                            f"[DELETE] Chunks remaining: "
                            f"{len(remaining_chunks)}"
                        )

                        if not remaining_chunks:
                            print("[DELETE] Successfully removed from ChromaDB")
                        else:
                            print("[DELETE] WARNING: Some chunks still remain")
                    else:
                        print("[DELETE] No chunks found in ChromaDB")

                    break

        state = [
            entry
            for entry in state
            if entry["raw_file_name"] not in deleted_files
        ]

        save_state(STATE_FILE_JSON, state)

        print("[DELETE] Removed deleted files from state JSON")

    # ---------------------------------------------------------
    # LOAD CURRENT KNOWLEDGE BASE FOR RETRIEVAL
    # ---------------------------------------------------------
    # state = load_state(STATE_FILE_JSON)
    # pdf_files = [entry["raw_file_name"] for entry in state]

    # pdf_docs = read_pdfs(pdf_files)
    web_docs = await read_websites_langchain_async()
    print("web_docs:", len(web_docs))

    documents = new_files + web_docs

    if not documents:
        print("\n[ERROR] No new PDFs or Websites found!")

    if web_docs:
        chunks = chunk_by_section_langchain(web_docs)

        for chunk in chunks:
            chunk["chunk_hash"] = generate_chunk_hash(chunk["text"])

    diagnostics.stop("3. Data Synchronization")

    # ---------------------------------------------------------
    # RETRIEVAL
    # ---------------------------------------------------------
    diagnostics.start("4. Hybrid Retrieval")
    retrieved_docs, vs, distances = retrieve(model)

    all_chunks = get_all_chunks()

    print(f"[BM25] Total chunks loaded from ChromaDB: {len(all_chunks)}")

    bm25_docs = retrieve_bm25(all_chunks)


    print("len of bm25_docs:", len(bm25_docs))

    if bm25_docs:
        print("bm25_docs[0]:", bm25_docs[0])

    # Merge and deduplicate
    # Merge and deduplicate DICTIONARIES based on their unique chunk_id
    combined_dict = {}
    for doc in retrieved_docs + bm25_docs:
        # Check if doc is a dictionary. If so, deduplicate by chunk_id
        if isinstance(doc, dict):
            chunk_id = doc.get("chunk_id", doc.get("text"))
            if chunk_id not in combined_dict:
                combined_dict[chunk_id] = doc
        else:
            # Fallback if your retrieve functions are still just returning strings
            if doc not in combined_dict:
                combined_dict[doc] = {"text": doc}
                
    combined_candidates = list(combined_dict.values())
    

    print(
        f"\n[RETRIEVAL] Pulled {len(retrieved_docs)} from Chroma, "
        f"{len(bm25_docs)} from BM25."
    )

    print(
        f"[RETRIEVAL] Total unique candidates sent to Reranker: "
        f"{len(combined_candidates)}"
    )

    diagnostics.stop("4. Hybrid Retrieval")
    # ---------------------------------------------------------
    # RERANK
    # ---------------------------------------------------------
    diagnostics.start("5. Cross-Encoder Reranking")
    reranked_docs = rerank_documents(
        reranker_model=reranker,
        retrieved_docs=combined_candidates,
    )
    diagnostics.stop("5. Cross-Encoder Reranking")

    # ---------------------------------------------------------
    # FINAL CONTEXT
    # ---------------------------------------------------------
    diagnostics.start("6. Context Packing")

    print("\n" + "=" * 80)
    print("FINAL CONTEXT PASSED TO LLM")
    print("=" * 80)

    final_context_list = []
    for idx, item in enumerate(reranked_docs):
        print(f"\n--- Chunk {idx + 1} ---")
        print(item)
        # Assuming item is a dict with a 'text' key. Adjust if it's a string.
        chunk_text = item.get("text", str(item)) if isinstance(item, dict) else str(item)
        final_context_list.append(chunk_text)
        
    final_context_string = "\n\n".join(final_context_list)
    
    diagnostics.stop("6. Context Packing")


    
    

    # 6. Generate answer
    diagnostics.start("7. LLM Generation")
    
    answer = generate_answer(reranked_docs)

    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(answer)

    diagnostics.stop("7. LLM Generation")

    diagnostics.generate_report(
        question=QUESTION, 
        retrieved_docs=reranked_docs, 
        answer=answer, 
        final_context=final_context_string
    )


    
    
    print("=" * 80)
	
	
if __name__ == "__main__":
    asyncio.run(main())