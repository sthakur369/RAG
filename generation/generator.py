import time
import ollama

from config.config import LLM_MODEL_NAME, LLM_TEMP, QUESTION
from utils.timing import print_timing


def create_prompt(
        documents: list[str],
        question: str = QUESTION
        ) -> str:

    texts = [
        doc["text"] if isinstance(doc, dict) else str(doc) 
        for doc in documents
    ]
    
    # Now join the extracted texts
    context = "\n\n---\n\n".join(texts)
    
    return f"""You are a precise technical assistant. Answer the question using ONLY the provided context.

RULES:
1. Do not use information outside the context.
2. If the context is insufficient, say: "I do not have enough information in the provided context to answer this."
3. Give the answer directly, but explain it with relevant details from the context. Avoid one-word or very short answers.
4. Do not add assumptions or introductory fluff.

<context>
{context}
</context>

<question>
{question}
</question>

Answer:"""



def generate_answer(documents):
    start = time.perf_counter()

    prompt = create_prompt(documents)

    response = ollama.chat(
        model=LLM_MODEL_NAME,
        messages=[{'role': 'user', 'content': prompt}],
        options={
            'temperature': LLM_TEMP  # <-- Force deterministic output
        }
        
    )

    print_timing(
        "generate_answer()",
        f"Generate answer with {LLM_MODEL_NAME}",
        start
    )

    return response["message"]["content"]