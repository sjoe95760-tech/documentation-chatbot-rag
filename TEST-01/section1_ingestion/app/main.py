"""
Section 1 — Ingestion Pipeline
Document upload -> extract -> chunk -> embed (primary + fallback) -> vector DB

Run with: uvicorn app.main:app --reload --port 8000
Docs at:  http://localhost:8000/docs
"""

import os
import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.extractor import extract_text
from app.chunker import chunk_text
from app.embedder import embed_chunks
from app.vectorstore import get_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion")

app = FastAPI(title="RAG Chatbot — Section 1: Ingestion Pipeline")

UPLOAD_DIR = Path("uploaded_docs")
UPLOAD_DIR.mkdir(exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm", ".md", ".docx"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document. Runs the full Section 1 pipeline:
    save -> extract -> chunk -> embed (with fallback) -> store in vector DB.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # 1. Save the uploaded file
    doc_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{doc_id}{ext}"
    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
        logger.info(f"Saved upload: {file.filename} -> {save_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # 2. Extract text (with page/section metadata where available)
    try:
        extracted = extract_text(save_path, ext)
    except Exception as e:
        logger.error(f"Extraction failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {e}")

    if not extracted:
        raise HTTPException(
            status_code=400,
            detail=(
                "No extractable text found in document. If this is an HTML "
                "file, it may be a JS-rendered page with no real content in "
                "the raw HTML (view-source and check). If it's a scanned "
                "PDF (images only, no text layer), OCR is required first — "
                "this pipeline does not include OCR."
            ),
        )

    # 3. Chunk the extracted text
    try:
        chunks = chunk_text(extracted, doc_name=file.filename)
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chunking failed: {e}")

    if not chunks:
        raise HTTPException(status_code=400, detail="Chunking produced no chunks")

    # 4. Embed chunks (primary embedder, falls back automatically on failure)
    try:
        embeddings, used_fallback = embed_chunks([c["text"] for c in chunks])
    except Exception as e:
        logger.error(f"Both primary and fallback embedding failed: {e}")
        raise HTTPException(status_code=500, detail="Embedding generation failed on all methods")

    # 5. Store in vector DB
    try:
        collection = get_collection()
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_name": file.filename,
                "doc_id": doc_id,
                "page": c.get("page"),
                "section": c.get("section"),
                "chunk_index": i,
            }
            for i, c in enumerate(chunks)
        ]
        documents = [c["text"] for c in chunks]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks for '{file.filename}' in vector DB")
    except Exception as e:
        logger.error(f"Vector DB storage failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vector DB storage failed: {e}")

    return JSONResponse(
        {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks_stored": len(chunks),
            "used_fallback_embedder": used_fallback,
            "status": "ready_for_retrieval",
        }
    )


@app.get("/documents")
def list_documents():
    """List distinct documents currently stored in the vector DB (for section 2 to query against)."""
    collection = get_collection()
    data = collection.get(include=["metadatas"])
    seen = {}
    for meta in data.get("metadatas", []):
        seen[meta["doc_id"]] = meta["document_name"]
    return [{"doc_id": k, "filename": v} for k, v in seen.items()]
