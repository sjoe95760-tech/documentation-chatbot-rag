import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

class BM25Retriever:
    def __init__(self):
        self.bm25 = None
        self.corpus_chunks = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple lowercase tokenization for keyword matching."""
        return re.findall(r'\w+', text.lower())

    def index_documents(self, raw_data: Dict[str, Any]):
        """Indexes stored text chunks into BM25 engine."""
        documents = raw_data.get("documents", [])
        metadatas = raw_data.get("metadatas", [])
        ids = raw_data.get("ids", [])

        self.corpus_chunks = []
        tokenized_corpus = []

        for idx, doc in enumerate(documents):
            chunk_item = {
                "id": ids[idx] if ids else str(idx),
                "text": doc,
                "metadata": metadatas[idx] if metadatas else {}
            }
            self.corpus_chunks.append(chunk_item)
            tokenized_corpus.append(self._tokenize(doc))

        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs keyword similarity search."""
        if not self.bm25 or not self.corpus_chunks:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get indices of top_k results
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only return non-zero matching scores
                chunk = self.corpus_chunks[idx]
                results.append({
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "score": float(scores[idx]),
                    "retrieval_method": "bm25_fallback"
                })
        return results