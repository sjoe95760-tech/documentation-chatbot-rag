\# Section 1 — Ingestion Pipeline



Document upload → extract → chunk → embed (primary + fallback) → vector DB.

This is the first third of the RAG documentation chatbot (Track 2). Section 2

(retrieval) and Section 3 (LLM answer generation) are built separately and

query the same ChromaDB store this service writes to.



\## What it does



1\. \*\*Upload\*\* — accepts PDF, HTML, Markdown, DOCX.

2\. \*\*Extract\*\* — pulls text out per file type, keeping page numbers (PDF) and

&#x20;  section/heading (HTML, MD, DOCX) as metadata. For HTML files that don't

&#x20;  use standard content tags (`<p>`, `<li>`, `<h1-3>`, etc — e.g. div/span-only

&#x20;  layouts), it automatically falls back to extracting all visible page text

&#x20;  rather than failing the upload.

3\. \*\*Chunk\*\* — splits into \~800-character overlapping chunks, metadata carried

&#x20;  along.

4\. \*\*Embed\*\* — primary embedder is OpenAI `text-embedding-3-small`. If that

&#x20;  call fails for any reason (no key, rate limit, network/timeout), it

&#x20;  automatically falls back to a local `sentence-transformers` model

&#x20;  (`all-MiniLM-L6-v2`) so ingestion doesn't hard-fail. This is logged and

&#x20;  also returned in the API response (`used\\\\\\\_fallback\\\\\\\_embedder`).

5\. \*\*Store\*\* — writes chunks + embeddings + metadata into a local, persisted

&#x20;  ChromaDB collection named `default`, stored on disk at `./chroma\\\\\\\_db`.





# ```Markdown (we are using local all-MiniLM-L6-v2 )

\## API Configuration

\* \*\*`OPENAI\\\_API\\\_KEY`\*\* (Optional): Used for primary chunk embeddings via `text-embedding-3-small`.

\* \*\*Fallback Behavior\*\*: If `OPENAI\\\_API\\\_KEY` is missing or fails, ingestion automatically falls back to the local `all-MiniLM-L6-v2` model via `sentence-transformers`.





# \## Setup



```bash

cd section1\\\\\\\_ingestion

python -m venv venv

venv\\\\\\\\Scripts\\\\\\\\activate        # Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

copy .env.example .env

\\\\# edit .env and add your OPENAI\\\\\\\_API\\\\\\\_KEY (optional — fallback works without it)

```



\## Run



```bash

python -m uvicorn app.main:app --reload --port 8000

```



Interactive API docs: http://localhost:8000/docs



\## Test it



```bash

curl -X POST http://localhost:8000/upload \\\\\\\\

\\\&#x20; -F "file=@/path/to/your/document.pdf"

```



Response:



```json

{

\\\&#x20; "doc\\\\\\\_id": "a1b2c3d4-...",

\\\&#x20; "filename": "document.pdf",

\\\&#x20; "chunks\\\\\\\_stored": 42,

\\\&#x20; "used\\\\\\\_fallback\\\\\\\_embedder": false,

\\\&#x20; "status": "ready\\\\\\\_for\\\\\\\_retrieval"

}

```



List documents currently in the store:



```bash

curl http://localhost:8000/documents

```



\## Testing the fallback path



Leave `OPENAI\\\\\\\_API\\\\\\\_KEY` unset (or set it to an invalid value) in `.env`, then

upload a file. The first call to `sentence-transformers` will download the

`all-MiniLM-L6-v2` model (\~90MB, one-time), then embed locally. Check the

response — `used\\\\\\\_fallback\\\\\\\_embedder` will be `true`, and the logs will show

`Primary embedder failed ... Falling back to local model.`



\## Output contract for Section 2 \& 3



Each stored chunk in ChromaDB (collection `default`, path `./chroma\\\\\\\_db`) has:



\- `documents`: the chunk text

\- `embeddings`: the vector

\- `metadatas`: `{ document\\\\\\\_name, doc\\\\\\\_id, page, section, chunk\\\\\\\_index }`



Section 2 and Section 3 read from this same collection.



⚠️ \*\*Important:\*\* Section 2 and Section 3 each cache their ChromaDB

connection when they start up. If you upload a new document here in

Section 1 while Section 2/3 are already running, \*\*restart Section 2 and

Section 3\*\* for the new document to become visible in retrieval/chat.



\## Architectural notes / trade-offs



\- \*\*Chunking is simple fixed-size with overlap\*\* (not semantic/recursive

&#x20; splitting) — fast to implement and good enough for a 1–2 day assessment.

&#x20; With more time: recursive character splitting or sentence-boundary aware

&#x20; chunking would preserve context better, especially for tightly-packed

&#x20; structured content like short list items.

\- \*\*Fallback embedder is local\*\* so it doesn't depend on the same third-party

&#x20; API that failed — a real resilience boundary, not just a second API key.

\- \*\*ChromaDB is persisted to local disk\*\* (`./chroma\\\\\\\_db`) rather than an

&#x20; external server — zero infra to run for the assessment, trivially swappable

&#x20; for Pinecone/Qdrant/Weaviate later since the vectorstore access is isolated

&#x20; in one module.

\- \*\*Page numbers\*\* are only available for PDFs; HTML/MD/DOCX get section

&#x20; headings instead — documented in the response format rather than faked.

\- \*\*No OCR.\*\* Scanned/image-only PDFs are not supported — extraction

&#x20; requires a real text layer.

