# it did not perform well so ignore it

import re
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# 1. Define the blacklist pattern once
EXCLUDED_SECTIONS_PATTERN = re.compile(
    r'\b(references|bibliography|summary|exercises)\b', 
    re.IGNORECASE
)

# ==========================================
# 1. TEXT CLEANING HELPERS (Same as before)
# ==========================================

def fix_broken_linebreaks(text: str) -> str:
    return re.sub(r'(\w+)\s*\n\s*([a-z])', r'\1 \2', text)

def remove_dynamic_headers_and_footers(text: str, min_repetitions: int = 2) -> str:
    valid_lines = [line.strip() for line in text.split('\n') if line.strip()]
    line_freq = {}
    for line in valid_lines:
        if len(line) < 120 and not line.startswith('#'):
            line_freq[line] = line_freq.get(line, 0) + 1
    boilerplate = {line for line, count in line_freq.items() if count >= min_repetitions}
    clean_lines = [line for line in text.split('\n') if line.strip() not in boilerplate]
    return '\n'.join(clean_lines)

# ==========================================
# 2. THE LLAMA-INDEX PIPELINE
# ==========================================

def chunk_by_section_llamaindex(
    documents: list[dict], 
    max_chars: int = 1500, 
    chunk_overlap: int = 150,
    min_chars: int = 250,        # The dynamic floor threshold
    absolute_max: int = 2000     # The absolute safety ceiling for embeddings
) -> list[dict]:
    
    final_chunks = []
    print(f"Total documents to process: {len(documents)}")

    # LlamaIndex Setup 1: Parses Markdown natively, injecting headers into metadata
    md_parser = MarkdownNodeParser()
    
    # LlamaIndex Setup 2: LlamaIndex splits by TOKENS, not characters.
    # We approximate your character limits (usually ~4 chars per token).
    token_chunk_size = max_chars // 4   # ~375 tokens
    token_overlap = chunk_overlap // 4  # ~37 tokens
    
    # SentenceSplitter respects paragraphs (\n\n) and sentences (. ) before splitting.
    char_splitter = SentenceSplitter(
        chunk_size=token_chunk_size,
        chunk_overlap=token_overlap
    )

    for doc in documents:
        source_name = doc['source']
        print(f"\n--- Processing Document: {source_name} ---")

        clean_text = fix_broken_linebreaks(doc["text"])
        clean_text = remove_dynamic_headers_and_footers(clean_text)

        # 1. Convert dictionary into a LlamaIndex native Document object
        llama_doc = Document(text=clean_text, metadata={"source": source_name})

        # 2. Parse by Markdown Headers (creates LlamaIndex "Nodes")
        section_nodes = md_parser.get_nodes_from_documents([llama_doc])

        # 3. Filter out blacklisted sections
        filtered_section_nodes = []
        for node in section_nodes:
            # LlamaIndex tracks hierarchy via metadata keys like 'Header_1', 'Header_2'
            section_titles = [str(v) for k, v in node.metadata.items() if k.startswith('Header_')]
            if not any(EXCLUDED_SECTIONS_PATTERN.search(title) for title in section_titles):
                filtered_section_nodes.append(node)

        # 4. Apply Size Bounding using Token Splits
        sized_nodes = char_splitter.get_nodes_from_documents(filtered_section_nodes)

        # ---------------------------------------------------------
        # Phase 3 - Dynamic Roll-Up (Identical Logic)
        # ---------------------------------------------------------
        doc_merged_chunks = []
        default_section = source_name.replace(".md", "").replace(".pdf", "").capitalize()

        for node in sized_nodes:
            content = node.text.strip()
            if not content:
                continue

            # Find the deepest specific header for the metadata (e.g., Header_3 over Header_1)
            header_keys = [k for k in node.metadata.keys() if k.startswith('Header_')]
            if header_keys:
                # 'Header_3' > 'Header_1', so reverse sort grabs the deepest hierarchy
                header_keys.sort(reverse=True)
                section_title = node.metadata.get(header_keys[0])
            else:
                section_title = default_section

            current_chunk_dict = {
                "text": content,
                "source": source_name,
                "section": section_title
            }

            if not doc_merged_chunks:
                doc_merged_chunks.append(current_chunk_dict)
                continue
                
            last_chunk = doc_merged_chunks[-1]
            combined_len = len(last_chunk["text"]) + len(current_chunk_dict["text"])

            needs_merge = (len(current_chunk_dict["text"]) < min_chars or len(last_chunk["text"]) < min_chars)

            if needs_merge and combined_len <= absolute_max:
                is_same_section = (last_chunk["section"].lower() == current_chunk_dict["section"].lower())

                if is_same_section:
                    last_chunk["text"] += f"\n\n{content}"
                else:
                    last_chunk["text"] += f"\n\n{current_chunk_dict['text']}"
                    last_chunk["section"] += f" & {current_chunk_dict['section']}"
            else:
                doc_merged_chunks.append(current_chunk_dict)

        # 5. Format final output explicitly for your ChromaDB schema
        for idx, chunk in enumerate(doc_merged_chunks):
            chunk["chunk_id"] = f"{source_name}_chunk_{idx}"
            chunk["text"] = f"[Section: {chunk['section']}]\n{chunk['text']}"
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
            print(chunk['text'])
            print('\n++++++++++++++\n')

    return final_chunks