import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_URL = os.getenv("DB_URL", f"sqlite:///{(BASE_DIR / 'sar.db').as_posix()}")

CHROMA_DIR = os.getenv("CHROMA_DIR", str(DATA_DIR / "chroma"))
CORPUS_DIR = os.getenv("CORPUS_DIR", str(DATA_DIR / "corpus"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

TOP_K = int(os.getenv("TOP_K", "4"))

PROHIBITED_PHRASES = [
    "definitely", "certainly", "guaranteed", "must be", "obvious", "clearly",
    "terrorist", "criminal",
]
