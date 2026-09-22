import re
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from config.config import (
    EXCLUDED_SECTIONS, 
    MAX_CHAR_IN_CHUNKS,
    MIN_CHAR_IN_CHUNKS,
    OVERLAP_CHAR_IN_CHUNKS,
    ABSOLUTE_MAX_CHAR_IN_CHUNKS
    )


# 1. Define the blacklist pattern once
EXCLUDED_SECTIONS_PATTERN = re.compile(
    rf"\b({'|'.join(map(re.escape, EXCLUDED_SECTIONS))})\b",
    re.IGNORECASE
)

# ==========================================
# 1. TEXT CLEANING HELPERS (Kept exactly as you had them)
# ==========================================

def fix_broken_linebreaks(text: str) -> str:
    """Stitches sentences broken across column or page margins."""
    return re.sub(r'(\w+)\s*\n\s*([a-z])', r'\1 \2', text)

def remove_dynamic_headers_and_footers(text: str, min_repetitions: int = 2) -> str:
    """Finds and removes recurring page headers/footers using line frequency."""
    valid_lines = [line.strip() for line in text.split('\n') if line.strip()]
    line_freq = {}
    for line in valid_lines:
        if len(line) < 120 and not line.startswith('#'):
            line_freq[line] = line_freq.get(line, 0) + 1
    boilerplate = {line for line, count in line_freq.items() if count >= min_repetitions}
    clean_lines = [line for line in text.split('\n') if line.strip() not in boilerplate]
    return '\n'.join(clean_lines)


# ==========================================
# 2. THE NEW LANGCHAIN PIPELINE
# ==========================================

def chunk_by_section_langchain(
    documents: list[dict], # its mandaotry becassue its default value is not set
    max_chars: int = MAX_CHAR_IN_CHUNKS, 
    chunk_overlap: int = OVERLAP_CHAR_IN_CHUNKS,
    min_chars: int = MIN_CHAR_IN_CHUNKS,        # The dynamic floor threshold
    absolute_max: int = ABSOLUTE_MAX_CHAR_IN_CHUNKS,     # The absolute safety ceiling for embeddings (~500 tokens)
    
) -> list[dict]:
    
    final_chunks = []
    print(f"Total documents to process: {len(documents)}")

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    for doc in documents:
        source_name = doc['source']
        print(f"\n--- Processing Document: {source_name} ---")

        clean_text = fix_broken_linebreaks(doc["text"])
        clean_text = remove_dynamic_headers_and_footers(clean_text)

        section_docs = md_splitter.split_text(clean_text)

        filtered_section_docs = []
        for s_doc in section_docs:
            section_titles = list(s_doc.metadata.values())
            if not any(EXCLUDED_SECTIONS_PATTERN.search(str(title)) for title in section_titles):
                filtered_section_docs.append(s_doc)

        sized_docs = char_splitter.split_documents(filtered_section_docs)

        # ---------------------------------------------------------
        # Phase 3 - Dynamic Roll-Up (With Smart Header Merging)
        # ---------------------------------------------------------
        doc_merged_chunks = []
        
        # Fallback for documents with no headers at all
        default_section = source_name.replace(".md", "").replace(".pdf", "").capitalize()

        for split_doc in sized_docs:
            content = split_doc.page_content.strip()
            if not content:
                continue

            metadata = split_doc.metadata
            section_title = metadata.get('Header 3', metadata.get('Header 2', metadata.get('Header 1', default_section)))
            
            # Create the dictionary WITH the header baked in (for standard chunks)
            current_chunk_dict = {
                "text": f"[Section: {section_title}]\n{content}",
                "source": source_name,
                "section": section_title
            }

            if not doc_merged_chunks:
                doc_merged_chunks.append(current_chunk_dict)
                continue
                
            last_chunk = doc_merged_chunks[-1]
            combined_len = len(last_chunk["text"]) + len(current_chunk_dict["text"])

            # Do we need to merge? (Is either chunk smaller than the floor?)
            needs_merge = (len(current_chunk_dict["text"]) < min_chars or len(last_chunk["text"]) < min_chars)

            if needs_merge and combined_len <= absolute_max:
                # Convert both to lowercase to ignore casing during comparison
                is_same_section = (last_chunk["section"].lower() == current_chunk_dict["section"].lower())

                if is_same_section:
                    # Same section? Just append the raw content, don't repeat the header
                    last_chunk["text"] += f"\n\n{content}"
                else:
                    # Different sections? Keep the double header for the LLM & update DB metadata
                    last_chunk["text"] += f"\n\n{current_chunk_dict['text']}"
                    last_chunk["section"] += f" & {current_chunk_dict['section']}"
            else:
                # No merge needed, just append as a new chunk
                doc_merged_chunks.append(current_chunk_dict)


        # Assign final Chunk IDs cleanly after all merges are complete
        for idx, chunk in enumerate(doc_merged_chunks):
            chunk["chunk_id"] = f"{source_name}_chunk_{idx}"
            final_chunks.append(chunk)

    # Diagnostics
    print("\n--- Chunking Summary ---")
    print(f"Total chunks created: {len(final_chunks)}")
    if final_chunks:
        sorted_chunks = sorted(final_chunks, key=lambda c: len(c["text"]), reverse=True)
        print("\nTop 3 Longest Chunks:")
        for chunk in sorted_chunks[:3]:
            print(f"  {chunk['chunk_id']}: {len(chunk['text'])} chars")

        print("\nTop 3 Shortest Chunks:")
        for chunk in sorted_chunks[-3:]:
            print(f"  {chunk['chunk_id']}: {len(chunk['text'])} chars")
        

    return final_chunks