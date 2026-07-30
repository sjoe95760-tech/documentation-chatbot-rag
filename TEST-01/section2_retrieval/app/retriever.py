# section2_retrieval/app/retriever.py

import logging
from typing import List, Dict, Any
from app.embedder import QueryEmbedder
from app.vectorstore import VectorStoreClient
from app.bm25_retriever import BM25Retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrievalPipeline:
    def __init__(self):
        self.embedder = QueryEmbedder()
        self.vectorstore = VectorStoreClient()
        self.bm25 = BM25Retriever()

    def retrieve(self, query: str, collection_name: str = "default", top_k: int = 5) -> List[Dict[str, Any]]:
        results = []
        
        try:
            query_vector, embed_provider = self.embedder.embed_query(query)
            raw_results = self.vectorstore.search(
                collection_name=collection_name, 
                query_vector=query_vector, 
                top_k=top_k
            )

            docs = raw_results["documents"][0]
            metas = raw_results["metadatas"][0]
            distances = raw_results["distances"][0]

            for text, meta, dist in zip(docs, metas, distances):
                # Standard L2 distance conversion: 1 / (1 + distance)
                similarity_score = round(1.0 / (1.0 + float(dist)), 4)
                
                results.append({
                    "text": text,
                    "metadata": meta,
                    "score": similarity_score,
                    "retrieval_method": f"vector_primary ({embed_provider})"
                })
            
            logger.info(f"Primary vector retrieval successful. Found {len(results)} chunks.")
            return results

        except Exception as e:
            logger.warning(f"[FALLBACK TRIGGERED] Vector retrieval failed: {e}. Executing BM25 fallback.")
            try:
                all_docs = self.vectorstore.get_all_documents(collection_name)
                self.bm25.index_documents(all_docs)
                return self.bm25.search(query=query, top_k=top_k)
            except Exception as bm25_err:
                logger.error(f"Fallback BM25 search failed completely: {bm25_err}")
                return []