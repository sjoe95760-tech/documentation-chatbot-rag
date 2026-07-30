from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.retriever import RetrievalPipeline

app = FastAPI(
    title="Documentation Chatbot - Section 2: Retrieval Pipeline",
    version="1.0.0"
)

pipeline = RetrievalPipeline()

class QueryRequest(BaseModel):
    query: str
    collection_name: Optional[str] = "default"
    top_k: Optional[int] = 5

class ChunkResponse(BaseModel):
    text: str
    metadata: Dict[str, Any]
    score: float
    retrieval_method: str

class QueryResponse(BaseModel):
    query: str
    total_retrieved: int
    chunks: List[ChunkResponse]

@app.post("/retrieve", response_model=QueryResponse)
def retrieve_chunks(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    chunks = pipeline.retrieve(
        query=request.query,
        collection_name=request.collection_name,
        top_k=request.top_k
    )

    return QueryResponse(
        query=request.query,
        total_retrieved=len(chunks),
        chunks=chunks
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "stage": "Section 2 Retrieval"}