from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.retrieval_client import RetrievalClient
from app.groundedness import GroundednessChecker
from app.llm_client import LLMClient
from app.formatter import ResponseFormatter
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env automatically

# Initialize FastAPI app ONCE
app = FastAPI(
    title="Section 3 - Generation Service",
    version="1.0.0"
)

# Add CORS Middleware right after app creation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from local HTML files
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever = RetrievalClient()
groundedness_checker = GroundednessChecker()
llm = LLMClient()
formatter = ResponseFormatter()

class ChatRequest(BaseModel):
    query: str
    collection_name: Optional[str] = "default"
    top_k: Optional[int] = 5

class SourceItem(BaseModel):
    document: str
    page: Optional[Any] = None
    section: Optional[Any] = None

class ChatResponse(BaseModel):
    query: str
    answer: str
    is_grounded: bool
    groundedness_reason: str
    llm_provider: str
    sources: List[SourceItem]
    suggested_followups: List[str]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Fetch retrieved chunks from Section 2
    chunks = await retriever.fetch_chunks(
        query=request.query,
        collection_name=request.collection_name,
        top_k=request.top_k
    )

    # 2. Perform Groundedness Check
    is_grounded, reason = groundedness_checker.evaluate(chunks)

    if not is_grounded:
        return ChatResponse(
            query=request.query,
            answer="Information is not available in the provided documentation.",
            is_grounded=False,
            groundedness_reason=reason,
            llm_provider="none",
            sources=[],
            suggested_followups=[]
        )

    # 3. Generate Answer using Primary/Fallback LLM
    answer, provider = await llm.generate_answer(request.query, chunks)

    # 4. Format Output with Sources and Follow-ups
    sources = formatter.format_sources(chunks)
    followups = formatter.generate_followup_questions(request.query)

    return ChatResponse(
        query=request.query,
        answer=answer,
        is_grounded=True,
        groundedness_reason=reason,
        llm_provider=provider,
        sources=sources,
        suggested_followups=followups
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "stage": "Section 3 Generation & Chat"}