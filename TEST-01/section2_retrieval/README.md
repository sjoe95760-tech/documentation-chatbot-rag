
# Section 2 — Retrieval Pipeline

Takes a user's question, embeds it, and returns the most relevant document chunks from the ChromaDB vector store created in Section 1[cite: 27]. This service exposes a `/retrieve` endpoint used by Section 3 (answer generation) to fetch context before calling the LLM[cite: 27].

---

## What It Does

1. **Receive Query** — Accepts natural language questions via `POST /retrieve`[cite: 27].
2. **Embed Query** — Embeds the query using the exact same model logic as Section 1 to ensure vector space alignment[cite: 27]:
   * **Primary:** OpenAI `text-embedding-3-small` (used if `OPENAI_API_KEY` is present and available)[cite: 27, 30].
   * **Fallback:** Local `sentence-transformers` (`all-MiniLM-L6-v2`), automatically triggered if the primary embedder fails or key is missing[cite: 27, 30].
3. **Vector Similarity Search** — Queries ChromaDB to find the `top_k` closest chunks, calculating normalized similarity scores using $1 / (1 + \text{L2 distance})$[cite: 27, 32].
4. **BM25 Keyword Fallback** — If vector retrieval fails (e.g., database down, missing collection, connection error), it gracefully falls back to a BM25 keyword search over all indexed chunk texts[cite: 27, 29, 32].
5. **Return Chunks** — Returns chunks containing text, source metadata (document name, page, section, `doc_id`), similarity scores, and attribution flags (`vector_primary (openai)`, `vector_primary (sentence-transformers)`, or `bm25_fallback`)[cite: 27, 32].

---

## Setup & Installation

### 1. Navigate and activate virtual environment
```bash
cd section2_retrieval
python -m venv venv

```

* **Windows:** `venv\Scripts\activate`

* **Mac/Linux:** `source venv/bin/activate`


### 2. Install dependencies

Install all required packages specified in `requirements.txt`:

```bash
pip install -r requirements.txt

```

### 3. Environment Variables (Optional)

No `.env` file is required to run keyless. However, if you want to use OpenAI embeddings:

* Create a `.env` file in `section2_retrieval/`.
* Set `OPENAI_API_KEY=your_openai_api_key`.


* If no key is set, the service automatically uses the local `all-MiniLM-L6-v2` model.



---

## Running the API

Start the FastAPI application on port 8001:

```bash
python -m uvicorn app.main:app --reload --port 8001

```

* **Base URL:** `http://localhost:8001`

* **Interactive API Docs:** `http://localhost:8001/docs`


---

## Testing & Usage

### Retrieve Chunks

```bash
curl -X POST http://localhost:8001/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How much does the Pro plan cost?",
    "collection_name": "default",
    "top_k": 5
  }'

```

**Sample API Response:**

```json
{
  "query": "How much does the Pro plan cost?",
  "total_retrieved": 5,
  "chunks": [
    {
      "text": "The Pro plan starts at $29/month...",
      "metadata": {
        "document_name": "pricing.pdf",
        "doc_id": "a1b2c3d4-...",
        "page": 2,
        "section": "Pricing Details",
        "chunk_index": 1
      },
      "score": 0.5156,
      "retrieval_method": "vector_primary (sentence-transformers)"
    }
  ]
}

```

---

## Dependency on Section 1

* **Database path:** Reads directly from Section 1's local ChromaDB store at `../section1_ingestion/chroma_db` (configurable via `CHROMA_DB_PATH` env variable).



> ⚠️ **Important — Restart Service After Ingesting New Files:**
> Section 2 initializes and caches its persistent ChromaDB connection on startup. If you upload new documents in Section 1 while Section 2 is actively running, **you must restart Section 2 (`Ctrl+C` and re-run)** for the newly ingested documents to be discoverable in `/retrieve` queries.
> 
> 

---

## Architectural Notes & Trade-offs

* **Resilient Graceful Degradation:** BM25 fallback is reserved specifically for vector DB infrastructure/connectivity failures, not low relevance scores. Low-relevance vector matches are intentionally passed downstream for Section 3's LLM groundedness evaluator to process.


* **Raw Distance Ordering:** Returns raw vector similarity results directly ordered by distance without applying secondary cross-encoder re-ranking.


* **No Deduplication:** Passes through matching chunks as stored; deduplication is deferred to upstream ingestion or downstream prompt construction.



```

```
