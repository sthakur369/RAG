import re
import hashlib

def normalize_chunk(text: str) -> str:

    # Removes double spaces, newlines, blank spaces
    clean_text = re.sub(r'\s+', ' ', text)
    return clean_text.strip().lower()

def generate_chunk_hash(text: str) -> str:

    # first normalize chunk
    clean_text = normalize_chunk(text)
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()
