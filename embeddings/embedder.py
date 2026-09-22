import time
from sentence_transformers import SentenceTransformer

from config.config import EMBEDDING_MODEL_NAME
from utils.timing import print_timing


def load_model():
    start = time.perf_counter()

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print_timing(
        "load_model()",
        "Load embedding model",
        start
    )

    return model


def embed_documents(model, documents):
    start = time.perf_counter()

    texts = [document["text"] for document in documents]
    embeddings = model.encode(texts)

    print_timing(
        "embed_documents()",
        "Create document embeddings",
        start
    )

    return embeddings


def embed_query(model, query):
    return model.encode(query)