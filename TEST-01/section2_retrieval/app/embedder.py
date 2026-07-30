import os
import logging
from typing import List
import openai
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryEmbedder:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.primary_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self._fallback_model = None

    @property
    def fallback_model(self):
        if self._fallback_model is None:
            logger.info("Loading fallback local embedding model...")
            self._fallback_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._fallback_model

    def embed_query(self, query: str) -> tuple[List[float], str]:
        """
        Embeds query using primary OpenAI API, with automatic fallback to local sentence-transformers.
        Returns tuple: (embedding_vector, provider_used)
        """
        if os.getenv("OPENAI_API_KEY"):
            try:
                response = self.openai_client.embeddings.create(
                    input=[query],
                    model=self.primary_model
                )
                return response.data[0].embedding, "openai"
            except Exception as e:
                logger.warning(f"Primary OpenAI embedder failed: {e}. Triggering local fallback.")
        
        # Fallback route
        embedding = self.fallback_model.encode(query).tolist()
        return embedding, "sentence-transformers"