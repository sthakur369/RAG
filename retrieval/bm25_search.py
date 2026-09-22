import bm25s
from config.config import (QUESTION, BM25_TOP_K)

def retrieve_bm25(
        chunks: list[dict], 
        top_k: int = BM25_TOP_K
        ) -> list[dict]: # Note: Changed return type to list[dict]
    
    """
    Indexes text chunks and retrieves the top_k matching chunks via BM25s.
    """
    # 1. Extract plain text strings for TOKENIZATION ONLY
    corpus_texts = [c["text"] if isinstance(c, dict) else c for c in chunks]

    # 2. Tokenize the text
    corpus_tokens = bm25s.tokenize(corpus_texts)

    # 3. Create the BM25 model and index the tokens
    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    # 4. Tokenize the user's query
    query_tokens = bm25s.tokenize(QUESTION)
    real_top_k = min(top_k, len(chunks))

    # 5. THE MAGIC TRICK: Pass the ORIGINAL `chunks` (dictionaries) as the corpus, 
    # not the plain text `corpus_texts`. BM25s will return the full dictionaries!
    results, scores = retriever.retrieve(query_tokens, corpus=chunks, k=real_top_k)

    # top_docs is now a flat list of your original dictionaries!
    top_docs = results[0].tolist()
    
    return top_docs