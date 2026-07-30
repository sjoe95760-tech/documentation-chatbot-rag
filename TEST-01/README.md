# Documentation Chatbot (RAG-based) — Track 2

An AI-powered documentation chatbot that answers questions strictly from
uploaded documentation (PDF, HTML, Markdown, DOCX) using
Retrieval-Augmented Generation. Every answer includes its source
document, page/section, and suggested follow-up questions. If the
answer isn't in the uploaded docs, it says so instead of guessing.

## Architecture

The system is split into three independent services, plus a static
chat UI, so each stage can be reasoned about, tested, and debugged in
isolation:

```
Upload → Extract → Chunk → Embed → Vector DB     (Section 1 — port 8000)
User question → Retrieve relevant chunks          (Section 2 — port 8001)
Chunks → Groundedness check → LLM answer → format  (Section 3 — port 8002)
Browser chat interface, calls Section 3 directly   (ui/index.html)
```

Each stage has a primary method and an automatic fallback, so a single
external API failure doesn't take down the whole pipeline:

|Stage|Primary|Fallback|Triggers when|
|-|-|-|-|
|Embeddings|OpenAI `text-embedding-3-small`|Local `sentence-transformers` (`all-MiniLM-L6-v2`)|API key missing/invalid, rate limit, timeout|
|Retrieval|Vector similarity search (ChromaDB)|BM25 keyword search|Vector DB unreachable/errors|
|Answer generation|Primary LLM (Groq / OpenAI, configurable)|Secondary LLM provider|API failure|

See `/section1\\\\\\\_ingestion/README.md`, `/section2\\\\\\\_retrieval/README.md`,
and `/section3\\\\\\\_generation/README.md` for service-specific details.

## Folder structure

```
section1\\\\\\\_ingestion/   Upload, extract, chunk, embed, store — FastAPI, port 8000
section2\\\\\\\_retrieval/   Query embedding + vector/BM25 retrieval — FastAPI, port 8001
section3\\\\\\\_generation/  Groundedness check, LLM answer, formatting — FastAPI, port 8002
ui/                   Static HTML/JS chat interface, calls Section 3 directly
```



# 

# Environment Variables \& API Setup



This project uses \*\*Groq\*\* (`llama-3.1-8b-instant`) as the primary LLM and \*\*OpenAI\*\* (`text-embedding-3-small`) as the primary embedder, with automatic local fallbacks if keys are missing or services time out.



1\. Create a `.env` file in the project root (or copy `.env.example`):

&#x20;  ```env

&#x20;  GROQ_API_KEY=gsk_API_KEY

&#x20;  PRIMARY\_LLM\_MODEL=llama-3.1-8b-instant

&#x20;  FALLBACK\_LLM\_MODEL=llama3



## Setup \& running

Each section has its own `requirements.txt` and `.env.example`. Set up
and run all three in **separate terminals**, in this order:

```cmd
:: Terminal 1
cd section1\\\\\\\_ingestion
python -m venv venv
venv\\\\\\\\Scripts\\\\\\\\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000

:: Terminal 2
cd section2\\\\\\\_retrieval
python -m venv venv
venv\\\\\\\\Scripts\\\\\\\\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001

:: Terminal 3
cd section3\\\\\\\_generation
python -m venv venv
venv\\\\\\\\Scripts\\\\\\\\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8002
```

Then open `ui/index.html` directly in a browser (double-click it —
no server needed for the UI itself).

### Uploading documents

Go to `http://127.0.0.1:8000/docs`, use the `/upload` endpoint to
upload a PDF, HTML, Markdown, or DOCX file. Then ask questions about
it in the chat UI.

## RAG pipeline explanation

1. **Upload** — file saved, format validated (PDF/HTML/MD/DOCX only).
2. **Extract** — text pulled out per format. PDFs keep page numbers;
HTML/MD/DOCX keep section headings where available.
3. **Chunk** — text split into \~800-character overlapping chunks so
embeddings stay focused and retrieval can return precise excerpts.
4. **Embed** — each chunk converted to a vector (primary: OpenAI,
fallback: local sentence-transformers) and stored in ChromaDB
alongside its source metadata (document name, page, section).
5. **Query** — when a question comes in, it's embedded the same way,
and the closest-matching chunks are retrieved (vector search,
falling back to BM25 keyword search if the vector DB errors).
6. **Groundedness check** — before calling the LLM, the retrieved
chunks are checked for relevance. If nothing relevant was found,
the system responds "not available in the provided documentation"
without calling the LLM at all — this prevents hallucination.
7. **Answer generation** — the LLM is given only the retrieved chunks
as context and asked to answer strictly from them.
8. **Formatting** — the response is packaged with the answer, cited
source(s) (document/page/section), and 3 suggested follow-up
questions.

## Known limitations / trade-offs

* **Stateless retrieval.** Each question is treated independently —
the system has no memory of earlier turns in the conversation.
Follow-up questions using pronouns like "that" or "it" without
restating the topic will not resolve correctly. This is a deliberate
scope decision for the assessment timeframe; a production version
would add conversation-aware query rewriting.
* **Per-process DB caching.** Section 2 and Section 3 each open their
own connection to the ChromaDB store at startup. If you upload a new
document via Section 1 while Section 2/3 are already running, they
will not see it until restarted. **Restart Section 2 and Section 3
after uploading new documents** for them to be visible in
retrieval/chat. A production fix would use ChromaDB's client-server
mode instead of per-process persistent clients, so all services
share one live connection.
* **Chunking is fixed-size, not semantic.** Simple \~800-character
overlapping chunks were used rather than sentence/paragraph-aware
splitting. This works well for prose-heavy documents but can
fragment tightly-packed structured content (e.g. short list items)
across chunk boundaries. With more time, recursive or
heading-aware chunking would improve retrieval precision on such
content.
* **No OCR.** Scanned PDFs (image-only, no text layer) are not
supported — text extraction requires a real text layer in the PDF.
* **Deduplication is not implemented.** Uploading the same file twice
creates two separate entries in the vector DB. Not harmful to
correctness, but not deduplicated.

## Demonstration

Verified successful queries across all four supported formats:

|#|Question|Source document|Result|
|-|-|-|-|
|1|"How many tracks are in the Technical Assessments document?"|`Technical\\\\\\\_Assessments\\\\\\\_Compiled.PDF`|✅ Correct, cited page 1|
|2|"What is Track 2 about in the Technical Assessments document?"|`Technical\\\\\\\_Assessments\\\\\\\_Compiled.PDF`|✅ Correct, cited page 1|
|3|"What is Aether?"|`TESTINGindex.html`|✅ Correct, cited HTML source|
|4|"How much does the CloudSync Plus plan cost?"|`cloudsync\\\\\\\_test.md`|✅ Correct — "$8/month"|
|5|"What fruits are listed in the unordered list?"|`Large Markdown Test File.md`|✅ Correct, full list returned|
|6|"What is the capital of France?" (unrelated to any doc)|—|✅ Correctly responded "not available in the provided documentation"|

Each response included correct source attribution and suggested
follow-up questions, as required by the response format spec.

