import os
import chromadb
from typing import List, Dict, Any

def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures all metadata values are valid ChromaDB primitives (str, int, float, bool)."""
    clean_meta = {}
    for key, value in metadata.items():
        if value is None:
            continue  # Drop None values that cause ChromaDB errors
        elif isinstance(value, (str, int, float, bool)):
            clean_meta[key] = value
        else:
            clean_meta[key] = str(value)  # Convert other objects to string
    return clean_meta

class CollectionWrapper:
    """Wraps ChromaDB collection to automatically sanitize metadata on .add() calls."""
    def __init__(self, collection):
        self._collection = collection

    def add(self, ids, documents=None, embeddings=None, metadatas=None, **kwargs):
        if metadatas:
            metadatas = [_sanitize_metadata(m) for m in metadatas]
        return self._collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            **kwargs
        )

    def __getattr__(self, name):
        return getattr(self._collection, name)

def get_client(db_path: str = "./chroma_db"):
    path = os.getenv("CHROMA_DB_PATH", db_path)
    return chromadb.PersistentClient(path=path)

def get_collection(name: str = "default", db_path: str = "./chroma_db"):
    """Exported function expected by section1 main.py"""
    client = get_client(db_path)
    raw_collection = client.get_or_create_collection(name=name)
    return CollectionWrapper(raw_collection)

class VectorStore:
    """Class interface for vector store access."""
    def __init__(self, db_path: str = "./chroma_db"):
        self.db_path = os.getenv("CHROMA_DB_PATH", db_path)
        self.client = chromadb.PersistentClient(path=self.db_path)

    def get_collection(self, name: str = "default"):
        raw_collection = self.client.get_or_create_collection(name=name)
        return CollectionWrapper(raw_collection)

    def add_chunks(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ):
        col = self.get_collection(collection_name)
        return col.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )