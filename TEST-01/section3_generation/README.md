
# Section 3 — Generation & Chat

Takes a user's question, retrieves relevant context from Section 2, evaluates whether the retrieved context supports an answer, generates a grounded response using an LLM, and formats it with source attribution and follow-up questions[cite: 34]. This service powers the main `/chat` endpoint used by the frontend UI[cite: 34].

---

## What It Does

1. **Receive Question** — Accepts questions via `POST /chat`[cite: 34].
2. **Fetch Context** — Uses `RetrievalClient` to call Section 2's `/retrieve` HTTP endpoint for context chunks[cite: 34, 40]. If Section 2 is unreachable, it gracefully handles the outage rather than crashing[cite: 34, 40].
3. **Groundedness Verification** — Evaluates retrieved similarity scores via `GroundednessChecker` before invoking any LLM[cite: 34, 37]. If no context is retrieved or the top similarity score is below the threshold (`0.2`), it immediately halts and returns *"Information is not available in the provided documentation."*[cite: 34, 37, 39]
4. **Grounded Answer Generation** — Sends context and question to `LLMClient` with strict non-hallucination instructions[cite: 34, 38]:
   * **Primary:** Groq API using `llama-3.1-8b-instant` via the OpenAI client interface[cite: 34, 38].
   * **Fallback:** Local Ollama endpoint (`llama3`) triggered automatically if Groq fails or the API key is omitted[cite: 34, 38].
5. **Response Formatting** — `ResponseFormatter` extracts deduplicated source locations (document name, page number, section heading) and constructs suggested follow-up questions[cite: 34, 36].

---

## Environment Configuration

Create a `.env` file in the `section3_generation/` directory:

```env
# Primary LLM Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here
PRIMARY_LLM_MODEL=llama-3.1-8b-instant

# Fallback LLM Configuration (Local Ollama)
OLLAMA_URL=http://localhost:11434/api/generate
FALLBACK_LLM_MODEL=llama3

# Upstream Services
RETRIEVAL_SERVICE_URL=[http://127.0.0.1:8001](http://127.0.0.1:8001)

```

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | Optional | — | Primary LLM key (get free at console.groq.com)

 |
| `PRIMARY_LLM_MODEL` | No | `llama-3.1-8b-instant` | Groq model selection

 |
| `OLLAMA_URL` | No | `http://localhost:11434/api/generate` | Local Ollama endpoint URL

 |
| `FALLBACK_LLM_MODEL` | No | `llama3` | Local Ollama model name

 |
| `RETRIEVAL_SERVICE_URL` | No | `http://127.0.0.1:8001` | URL of Section 2 Retrieval API

 |

---

## Setup & Installation

### 1. Create and activate virtual environment

```bash
cd section3_generation
python -m venv venv

```

* **Windows:** `venv\Scripts\activate`

* **Mac/Linux:** `source venv/bin/activate`


### 2. Install dependencies

Ensure all requirements are installed:

```bash
pip install -r requirements.txt

```

### 3. Environment File

Copy `.env.example` to `.env` and add your `GROQ_API_KEY` if using Groq:

```bash
cp .env.example .env     # Windows: copy .env.example .env

```

---

## Running the Service

> ⚠️ **Prerequisites:** Section 1 (port 8000) and Section 2 (port 8001) must be running first.
> 
> 

Start the FastAPI application on port 8002:

```bash
python -m uvicorn app.main:app --reload --port 8002

```

* **Base URL:** `http://localhost:8002`

* **Interactive API Docs:** `http://localhost:8002/docs`


---

## Testing & Usage

### Send a Chat Query

```bash
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How much does the Pro plan cost?",
    "collection_name": "default",
    "top_k": 5
  }'

```

**Sample Grounded Response:**

```json
{
  "query": "How much does the Pro plan cost?",
  "answer": "According to the provided context, the Pro plan costs $8/month.",
  "is_grounded": true,
  "groundedness_reason": "Context sufficient for grounded response.",
  "llm_provider": "Primary Groq (llama-3.1-8b-instant)",
  "sources": [
    {
      "document": "cloudsync_test.md",
      "page": null,
      "section": "Pricing"
    }
  ],
  "suggested_followups": [
    "Can you explain more details regarding how much does the pro plan cost?",
    "What are the prerequisites or related configurations for this?",
    "Are there any common troubleshooting steps for this topic?"
  ]
}

```

---

## Architectural Notes & Trade-offs

* **Score-Based Groundedness Gate:** Groundedness checks evaluate candidate vector distance scores against a pre-set threshold (`0.2`) prior to generation. This drastically cuts token costs and eliminates hallucination on out-of-domain prompts.


* **True Local Fallback Execution:** Uses local Ollama via standard HTTP requests as a secondary provider. In the event of a Groq API failure or missing API key, the system seamlessly transitions to local inference without failing the request.


* **CORS Middleware Support:** Enables direct browser calls from local web interfaces or standalone HTML pages.



```

```
