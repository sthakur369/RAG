# all logics are handmade so code is too long. So ignore it

import re

def slice_oversized_block(
    block: str, 
    max_chars: int = 1500, 
    overlap_words: int = 25
) -> list[str]:
    """
    Splits an oversized block cleanly at word boundaries (spaces),
    maintaining a meaningful multi-word overlap between pieces.
    """
    words = block.split()
    chunks = []
    current_words = []
    current_len = 0

    for word in words:
        # +1 accounts for the space between words
        word_len = len(word) + 1 

        if current_len + word_len > max_chars and current_words:
            # Save the current chunk
            chunks.append(" ".join(current_words))
            
            # Step back by 'overlap_words' so context bridges smoothly
            overlap = current_words[-overlap_words:] if len(current_words) > overlap_words else current_words
            current_words = list(overlap) + [word]
            current_len = sum(len(w) + 1 for w in current_words)
        else:
            current_words.append(word)
            current_len += word_len

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks

# ==========================================
# 1. TEXT CLEANING HELPERS
# ==========================================

def fix_broken_linebreaks(text: str) -> str:
    """Stitches sentences broken across column or page margins."""
    return re.sub(r'(\w+)\s*\n\s*([a-z])', r'\1 \2', text)

def remove_dynamic_headers_and_footers(text: str, min_repetitions: int = 2) -> str:
    """Finds and removes recurring page headers/footers using line frequency."""
    
    # Extract non-empty lines
    valid_lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Count occurrences of short lines (ignore Markdown headings)
    line_freq = {}
    for line in valid_lines:
        if len(line) < 120 and not line.startswith('#'):
            line_freq[line] = line_freq.get(line, 0) + 1

    # Identify boilerplate (lines repeating >= min_repetitions)
    boilerplate = {line for line, count in line_freq.items() if count >= min_repetitions}

    # Rebuild text excluding the repeating boilerplate
    clean_lines = [line for line in text.split('\n') if line.strip() not in boilerplate]
    return '\n'.join(clean_lines)


# ==========================================
# 2. CHUNKING HELPERS
# ==========================================

def split_into_sentences(text: str) -> list[str]:
    """Splits text by punctuation (.?!) without breaking decimals or abbreviations."""
    sentence_end = re.compile(r'(?<=[.?!])\s+(?=[A-Z0-9])')
    sentences = sentence_end.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]

def split_large_section(
    text: str,
    section_title: str,
    source: str,
    start_idx: int,
    max_chars: int = 1500
) -> tuple[list[dict], int]:
    sub_chunks = []
    chunk_idx = start_idx
    sentences = split_into_sentences(text)
    
    current_sentences = []
    current_char_count = 0

    for sent in sentences:
        sent_len = len(sent) + 1

        # Fallback: if a single block/sentence exceeds max_chars
        if sent_len > max_chars:
            # 1. Flush whatever was buffered so far
            if current_sentences:
                chunk_body = " ".join(current_sentences)
                sub_chunks.append({
                    "text": f"[Section: {section_title}]\n{chunk_body}",
                    "source": source,
                    "section": section_title,
                    "chunk_id": f"{source}_chunk_{chunk_idx}"
                })
                chunk_idx += 1
                current_sentences = []
                current_char_count = 0

            # 2. Slice cleanly on word boundaries with a 25-word overlap
            pieces = slice_oversized_block(sent, max_chars=max_chars, overlap_words=25)
            for piece in pieces:
                sub_chunks.append({
                    "text": f"[Section: {section_title}]\n{piece}",
                    "source": source,
                    "section": section_title,
                    "chunk_id": f"{source}_chunk_{chunk_idx}"
                })
                chunk_idx += 1
            continue

        # Standard sentence accumulation with 1-sentence overlap
        if current_char_count + sent_len > max_chars and current_sentences:
            chunk_body = " ".join(current_sentences)
            sub_chunks.append({
                "text": f"[Section: {section_title}]\n{chunk_body}",
                "source": source,
                "section": section_title,
                "chunk_id": f"{source}_chunk_{chunk_idx}"
            })
            chunk_idx += 1

            overlap_sent = current_sentences[-1]
            current_sentences = [overlap_sent, sent]
            current_char_count = len(overlap_sent) + 1 + sent_len
        else:
            current_sentences.append(sent)
            current_char_count += sent_len

    if current_sentences:
        chunk_body = " ".join(current_sentences)
        sub_chunks.append({
            "text": f"[Section: {section_title}]\n{chunk_body}",
            "source": source,
            "section": section_title,
            "chunk_id": f"{source}_chunk_{chunk_idx}"
        })
        chunk_idx += 1

    return sub_chunks, chunk_idx

# ==========================================
# 3. MAIN PIPELINE
# ==========================================

def chunk_by_section(
    documents: list[dict], 
    max_chars: int = 1500, 
    min_chars: int = 250
) -> list[dict]:
    """Main orchestrator: cleans, splits by sections, and enforces size limits."""
    chunks = []
    print(f"Total documents to process: {len(documents)}")

    for doc in documents:
        source_name = doc['source']
        print(f"\n--- Processing Document: {source_name} ---")

        # 1. Clean document text
        text = fix_broken_linebreaks(doc["text"])
        text = remove_dynamic_headers_and_footers(text)

        # 2. Split into paragraphs
        paragraphs = re.split(r'\n\s*\n+', text)

        section_title = "General"
        section_body = ""
        pending_prefix = ""  # Holds tiny sections to carry forward
        chunk_idx = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            # Skip empty lines or lone page numbers
            if not paragraph or len(paragraph) < 3 or re.match(r'^\d+$', paragraph):
                continue

            # 3. Handle Markdown headings (New Section Boundary)
            if re.match(r'^#{1,6}\s+', paragraph):
                
                # Save the previous section's content before starting the new one
                if section_body:
                    text_to_process = f"{pending_prefix}\n\n{section_body}".strip() if pending_prefix else section_body.strip()
                    pending_prefix = ""

                    # CASE A: Oversized -> Split with sentence overlap
                    if len(text_to_process) > max_chars:
                        sub_chunks, chunk_idx = split_large_section(
                            text=text_to_process,
                            section_title=section_title,
                            source=source_name,
                            start_idx=chunk_idx,
                            max_chars=max_chars
                        )
                        chunks.extend(sub_chunks)

                    # CASE B: Too small (< min_chars) -> Carry over as prefix
                    elif len(text_to_process) < min_chars:
                        pending_prefix = f"[{section_title}] {text_to_process}"

                    # CASE C: Balanced -> Save directly
                    else:
                        chunks.append({
                            "text": f"[Section: {section_title}]\n{text_to_process}",
                            "source": source_name,
                            "section": section_title,
                            "chunk_id": f"{source_name}_chunk_{chunk_idx}"
                        })
                        chunk_idx += 1

                    section_body = ""

                # Extract new section name (strip hashes/bold marks)
                section_title = re.sub(r'^#{1,6}\s*|\*{1,2}', '', paragraph).strip()

                # Skip bibliography/references completely
                if re.search(r'\b(references|bibliography|summary|exercises)\b', section_title, re.IGNORECASE):
                    continue
                continue

            # Skip accumulating text if we are in References
            if re.search(r'\b(references|bibliography)\b', section_title, re.IGNORECASE):
                continue

            # 4. Accumulate paragraphs into the current section
            if not section_body:
                section_body = paragraph
            else:
                section_body += f"\n\n{paragraph}"

        # 5. Flush trailing buffer at the end of the document
        if section_body or pending_prefix:
            text_to_process = f"{pending_prefix}\n\n{section_body}".strip() if pending_prefix else section_body.strip()

            if len(text_to_process) > max_chars:
                sub_chunks, chunk_idx = split_large_section(
                    text=text_to_process,
                    section_title=section_title,
                    source=source_name,
                    start_idx=chunk_idx,
                    max_chars=max_chars
                )
                chunks.extend(sub_chunks)
            elif len(text_to_process) < min_chars and chunks:
                # Merge tiny trailing orphan backward into the last chunk
                chunks[-1]["text"] += f"\n\n{text_to_process}"
            elif text_to_process:
                chunks.append({
                    "text": f"[Section: {section_title}]\n{text_to_process}",
                    "source": source_name,
                    "section": section_title,
                    "chunk_id": f"{source_name}_chunk_{chunk_idx}"
                })

    # ==========================================
    # 4. DIAGNOSTICS & SUMMARY
    # ==========================================
    print("\n--- Chunking Summary ---")
    print(f"Total chunks created: {len(chunks)}")

    if chunks:
        # for i in range(min(3, len(chunks))):
        #     print(f"\nchunks {i}: {chunks[i]}")

        sorted_chunks = sorted(chunks, key=lambda c: len(c["text"]), reverse=True)
        print("\nChunk lengths (descending):")
        for chunk in sorted_chunks:
            print(f"{chunk['chunk_id']}: {len(chunk['text'])} characters")
    else:
        print("Warning: No chunks were created. Check if your documents contain text.")

    return chunks