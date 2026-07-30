\# Section 2 — Retrieval Pipeline



Takes a user's question, embeds it, and returns the most relevant

document chunks from the vector store built by Section 1. This is the

middle third of the RAG documentation chatbot (Track 2). Section 3

(answer generation) calls this service's `/retrieve` endpoint to get

context before asking the LLM to answer.



\## What it does



1\. \*\*Receive a query\*\* — a natural language question via `/retrieve`.

2\. \*\*Embed the query\*\* — using the same model family as Section 1's

&#x20;  ingestion, so query and stored chunks live in the same vector space:

&#x20;  - Primary: OpenAI `text-embedding-3-small` (used if `OPENAI\_API\_KEY`

&#x20;    is set and the call succeeds)

&#x20;  - Fallback: local `sentence-transformers` (`all-MiniLM-L6-v2`),

&#x20;    triggered automatically on any primary failure

3\. \*\*Vector similarity search\*\* — queries the ChromaDB collection

&#x20;  written by Section 1, returns the top-k closest chunks with a

&#x20;  similarity score (`1 / (1 + L2 distance)`).

4\. \*\*BM25 keyword fallback\*\* — if the vector search fails entirely

&#x20;  (DB unreachable, collection error, etc.), it falls back to a

&#x20;  keyword-based BM25 search over the same stored chunk texts, so

&#x20;  retrieval degrades gracefully instead of failing outright.

5\. \*\*Return chunks\*\* — each result includes the chunk text, full

&#x20;  metadata (document name, page, section, doc\_id), a relevance

&#x20;  score, and which retrieval method produced it

&#x20;  (`vector\_primary (...)` or `bm25\_fallback`).



\## Setup



```bash

cd section2\_retrieval

python -m venv venv

venv\\Scripts\\activate        # Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

```



No `.env` file is required to run — `OPENAI\_API\_KEY` is optional (only

used if present; the fallback embedder works without any key).



\## Run



```bash

python -m uvicorn app.main:app --reload --port 8001

```



Interactive API docs: http://localhost:8001/docs



\## Test it



```bash

curl -X POST http://localhost:8001/retrieve \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{

&#x20;   "query": "How much does the Pro plan cost?",

&#x20;   "collection\_name": "default",

&#x20;   "top\_k": 5

&#x20; }'

```



Response:



```json

{

&#x20; "query": "How much does the Pro plan cost?",

&#x20; "total\_retrieved": 5,

&#x20; "chunks": \[

&#x20;   {

&#x20;     "text": "...",

&#x20;     "metadata": { "document\_name": "...", "page": null, "section": "Pricing", "doc\_id": "...", "chunk\_index": 1 },

&#x20;     "score": 0.5156,

&#x20;     "retrieval\_method": "vector\_primary (sentence-transformers)"

&#x20;   }

&#x20; ]

}

```



\## Depends on Section 1



Reads from the same ChromaDB store that Section 1 writes to:

collection name `default`, path `../section1\_ingestion/chroma\_db`

(configurable via the `CHROMA\_DB\_PATH` environment variable).



⚠️ \*\*Important — restart after new uploads.\*\* This service opens its

ChromaDB connection once at startup and caches it. If a document is

uploaded via Section 1 \*after\* this service has already started,

it will not appear in retrieval results until this service is

restarted. This was confirmed during testing: newly uploaded documents

were invisible to `/retrieve` until `Ctrl+C` + restart, even though

`GET /documents` on Section 1 correctly showed them as stored.



\## Architectural notes / trade-offs



\- \*\*BM25 fallback triggers on vector search failure, not on low

&#x20; relevance.\*\* If the vector DB is reachable but simply returns weak

&#x20; matches, that's treated as a retrieval quality issue for Section 3's

&#x20; groundedness check to handle — not an outage that should activate a

&#x20; different search method. BM25 fallback is specifically for when the

&#x20; vector path is broken (DB down, collection missing, network error).

\- \*\*No result deduplication.\*\* If the same document was uploaded more

&#x20; than once, duplicate chunks may appear in results. Section 1 doesn't

&#x20; dedupe on upload, so this is inherited here.

\- \*\*`top\_k` is a simple integer, no re-ranking.\*\* Retrieved chunks are

&#x20; returned in raw similarity order. With more time, a re-ranking step

&#x20; (e.g. cross-encoder) could improve precision, especially when many

&#x20; documents are mixed in the same collection.

