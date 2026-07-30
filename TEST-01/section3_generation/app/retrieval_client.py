# section3_generation/app/retrieval_client.py

import os
import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RetrievalClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = os.getenv("RETRIEVAL_SERVICE_URL", base_url)

    async def fetch_chunks(self, query: str, collection_name: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/retrieve",
                    json={
                        "query": query,
                        "collection_name": collection_name,
                        "top_k": top_k
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("chunks", [])
                else:
                    logger.warning(f"Section 2 returned status code {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Could not connect to Section 2 Retrieval API: {e}")
                return []