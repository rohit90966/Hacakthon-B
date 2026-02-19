import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from .config import CHROMA_DIR, CORPUS_DIR


class RAGRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="sar_corpus",
            embedding_function=self.embedder,
        )

    def load_corpus(self, corpus_dir=None):
        corpus_path = Path(corpus_dir or CORPUS_DIR)
        docs = []
        ids = []
        for idx, path in enumerate(sorted(corpus_path.glob("*.txt"))):
            docs.append(path.read_text(encoding="utf-8"))
            ids.append(path.stem)
        if docs:
            self.collection.upsert(documents=docs, ids=ids)

    def retrieve(self, query, top_k=4):
        if not query:
            return []
        res = self.collection.query(query_texts=[query], n_results=top_k)
        docs = res.get("documents", [[]])[0]
        ids = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        results = []
        for doc_id, doc, dist in zip(ids, docs, distances):
            results.append({
                "doc_id": doc_id,
                "text": doc,
                "similarity": round(1 - dist, 4) if dist is not None else None,
            })
        return results
