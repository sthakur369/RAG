import re
import hashlib

def normalize_text(text: str) -> str:

    # Removes double spaces, newlines, blank spaces
    clean_text = re.sub(r'\s+', ' ', text)
    return clean_text.strip().lower()

def generate_chunk_hash(text: str) -> str:

    # first normalize chunk
    clean_text = normalize_text(text)
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

def generate_chunk_id(source_name: str, chunk_index: int, text_hash: str) -> str:
    
    # Creates a guaranteed unique, traceable ID. 
    # Example: rag_101.pdf_chunk_0
    
    return f"{source_name}_chunk_{chunk_index}"