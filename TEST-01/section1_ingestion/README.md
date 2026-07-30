Markdown
# Section 1 — Ingestion Pipeline

Document upload → extract → chunk → embed (primary + fallback) → vector DB.

This is the first third of the RAG documentation chatbot (Track 2). Section 2 (retrieval) and Section 3 (LLM answer generation) are built separately and query the same ChromaDB store this service writes to.

---

## What It Does

1. **Upload** — Accepts PDF, HTML, Markdown, and DOCX files.
2. **Extract** — Pulls text per file type while retaining page numbers (PDF) and section/heading titles (HTML, MD, DOCX) as metadata. If an HTML file lacks standard tags (`<p>`, `<li>`, `<h1-3>`), it automatically falls back to full-page text extraction.
3. **Chunk** — Splits text into ~800-character overlapping chunks (~150 character overlap), preserving all metadata attributes on each chunk.
4. **Embed** — Primary embedder uses OpenAI `text-embedding-3-small`. If `OPENAI_API_KEY` is missing or the call fails (rate limits, timeouts, offline mode), it automatically falls back to the local `sentence-transformers` model (`all-MiniLM-L6-v2`) so ingestion never fails.
5. **Store** — Sanitizes metadata and writes chunks, embeddings, and metadata into a persistent local ChromaDB collection named `default` at `./chroma_db`.

---

## Setup & Installation

### 1. Create and activate a virtual environment
```bash
cd section1_ingestion
python -m venv venv
Windows: venv\Scripts\activate

Mac/Linux: source venv/bin/activate

2. Install dependencies
Make sure to install all required packages specified in requirements.txt:

Bash
pip install -r requirements.txt
3. Environment Configuration
Copy the sample environment file to create your .env:

Bash
cp .env.example .env     # On Windows Command Prompt: copy .env.example .env
API Key Options:

To use OpenAI embeddings: Open .env and set OPENAI_API_KEY=your_actual_key.

To run completely keyless / offline: Leave OPENAI_API_KEY empty or unset in .env. The system will automatically use the local all-MiniLM-L6-v2 model.

Running the API
Start the FastAPI application with Uvicorn:

Bash
python -m uvicorn app.main:app --reload --port 8000
API Endpoint: http://localhost:8000

Interactive Swagger Docs: http://localhost:8000/docs

Testing & Usage
Upload a Document
Bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/document.pdf"
Sample API Response:

JSON
{
  "doc_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "filename": "document.pdf",
  "chunks_stored": 42,
  "used_fallback_embedder": false,
  "status": "ready_for_retrieval"
}
(Note: used_fallback_embedder will be true if running without an OPENAI_API_KEY).

List Stored Documents
Bash
curl http://localhost:8000/documents
Testing the Fallback Path
Unset or leave OPENAI_API_KEY empty in .env.

Upload any file via /upload.

On the first run, sentence-transformers will download the local all-MiniLM-L6-v2 model (~90MB, one-time).

Verify that used_fallback_embedder returns true in the API response.

Output Contract for Section 2 & Section 3
Each chunk stored in ChromaDB (collection default, path ./chroma_db) follows this schema:

documents: Chunk string content.

embeddings: 1536-dim (OpenAI) or 384-dim (SentenceTransformers) vector array.

metadatas: { document_name, doc_id, page, section, chunk_index }

⚠️ Important: Section 2 and Section 3 cache their ChromaDB connections on initial startup. If you ingest new documents here while Section 2 or 3 are actively running, restart Section 2 and 3 to pick up the new vector embeddings.

Architectural Notes & Trade-offs
Fixed-size chunking: Uses 800-character blocks with 150-character overlap for simplicity and speed.

Resilient embedding fallback: A local model boundary ensures document ingestion remains functional even during third-party API outages or offline development.

Local vector storage: ChromaDB is persisted to disk (./chroma_db) avoiding external infrastructure dependencies while remaining easily swappable for cloud vector DBs (Pinecone, Qdrant, Weaviate).

Metadata extraction: Section headers are extracted for HTML, Markdown, and DOCX, while page numbers are extracted specifically for PDF files.
