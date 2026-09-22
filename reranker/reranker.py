from sentence_transformers import CrossEncoder
from config.config import (QUESTION, RERANKER_TOP_K, RERANKER_MODEL_NAME)

def load_reranker(model_name: str = RERANKER_MODEL_NAME):
    """
    Initializes and loads the Cross-Encoder model.
    """
    print(f"[TIMING] Loading Reranker Model: {model_name}...")
    model = CrossEncoder(model_name, max_length=512)
    return model

def rerank_documents(
    reranker_model: CrossEncoder, 
    retrieved_docs: list, # Removed [str] to allow dictionaries
    query: str = QUESTION, 
    top_n: int = RERANKER_TOP_K
) -> list:
    if not retrieved_docs:
        return []

    # 1. Safely extract text for the model (handles both dicts and raw strings)
    sentence_pairs = []
    for doc in retrieved_docs:
        text = doc["text"] if isinstance(doc, dict) else str(doc)
        sentence_pairs.append([query, text])

    # 2. Predict the relevance scores
    scores = reranker_model.predict(sentence_pairs)

    # 3. Combine scores with the ORIGINAL documents and sort
    scored_docs = list(zip(scores, retrieved_docs))
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    print("\n--- Reranker Scores ---")
    final_results = []
    
    # 4. Inject the score and ensure the output is a dictionary
    for idx, (score, doc) in enumerate(scored_docs[:top_n]):
        text = doc["text"] if isinstance(doc, dict) else str(doc)
        preview = text[:80].replace('\n', ' ') + "..."
        print(f"Rank {idx+1} | Score: {score:.4f} | {preview}")
        
        # If it's a dictionary, attach the score. 
        if isinstance(doc, dict):
            doc["rerank_score"] = float(score)
            final_results.append(doc)
        else:
            # If it's a string, wrap it in a dict so the evaluator doesn't crash
            final_results.append({
                "text": text,
                "rerank_score": float(score),
                "source": "Unknown (Lost in Retrieval)",
                "chunk_id": "N/A"
            })

    return final_results