# section2_retrieval/app/vectorstore.py

import os
import chromadb

class VectorStoreClient:
    def __init__(self, db_path: str = "../section1_ingestion/chroma_db"):
        self.db_path = os.getenv("CHROMA_DB_PATH", db_path)
        self.client = chromadb.PersistentClient(path=self.db_path)

    def search(self, collection_name: str, query_vector: list, top_k: int = 5):
        """Perform vector similarity search safely."""
        try:
            collection = self.client.get_collection(name=collection_name)
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception:
            # If collection doesn't exist yet, return empty structure
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def get_all_documents(self, collection_name: str):
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.get(include=["documents", "metadatas"])
        except Exception:
            return {"documents": [], "metadatas": [], "ids": []}