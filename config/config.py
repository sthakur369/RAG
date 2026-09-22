STATE_FILE_JSON = "data/files/files_state.json"
STATE_WEBSITE_JSON = "data/websites/files_state.json"

FILES_INPUT_FOLDER = "data/files/raw_files"
FILES_OUTPUT_FOLDER = "data/files/md_files"

WEBSITES_INPUT_FOLDER = "data/websites/websites.txt"
WEBSITES_OUTPUT_FOLDER = "data/websites/md_files"

MAX_CONCURRENT_REQUESTS = 10

EXCLUDED_SECTIONS = [ "references", "bibliography", "summary", "exercises" ]

MAX_CHAR_IN_CHUNKS = 1500
MIN_CHAR_IN_CHUNKS = 250
OVERLAP_CHAR_IN_CHUNKS = 150
ABSOLUTE_MAX_CHAR_IN_CHUNKS = 2000

CHROMA_DB_PATH = "chroma_database"
COLLECTION_NAME = "knowledge_base"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CHUNKING_STRATEGY = "section"

TOP_K = 50
BM25_TOP_K = 50
RERANKER_TOP_K = 5

LLM_MODEL_NAME = "gemma3:4b"
LLM_TEMP = 0.3

QUESTION = "When was RAG first introduced?"

