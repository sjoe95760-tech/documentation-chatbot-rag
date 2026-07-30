\# Section 3 — Generation \& Chat



Takes a user's question, retrieves relevant context from Section 2,

checks whether that context actually supports an answer, generates a

grounded response with an LLM, and formats it with sources and

follow-up questions. This is the final third of the RAG documentation

chatbot (Track 2) — the `/chat` endpoint the UI talks to.



\## What it does



1\. \*\*Receive a question\*\* — via `POST /chat`.

2\. \*\*Fetch context\*\* — calls Section 2's `/retrieve` endpoint

&#x20;  (`RetrievalClient`) to get the top-k most relevant chunks for the

&#x20;  question. If Section 2 is unreachable or errors, this returns an

&#x20;  empty chunk list rather than crashing.

3\. \*\*Groundedness check\*\* — before calling the LLM at all,

&#x20;  `GroundednessChecker` looks at the retrieved chunks' relevance

&#x20;  scores. If no chunks were retrieved, or the best score is below a

&#x20;  threshold (default `0.2`), the endpoint immediately returns

&#x20;  \*"Information is not available in the provided documentation"\*

&#x20;  without calling the LLM — this is what prevents hallucinated

&#x20;  answers when the uploaded docs don't cover the question.

4\. \*\*Generate answer\*\* — if grounded, `LLMClient` sends the question

&#x20;  plus retrieved context to an LLM with a strict system prompt

&#x20;  ("answer only from the provided context; say you don't know if it

&#x20;  isn't there"):

&#x20;  - Primary: Groq API (OpenAI-compatible client, model

&#x20;    `llama-3.1-8b-instant` by default)

&#x20;  - Fallback: local Ollama model (`llama3` by default), used

&#x20;    automatically if the Groq call fails for any reason

5\. \*\*Format response\*\* — `ResponseFormatter` extracts deduplicated

&#x20;  source citations (document name, page, section) from the chunks

&#x20;  actually used, and generates 3 template-based follow-up questions

&#x20;  based on the original query.



## API Configuration
* **`GROQ_API_KEY`** (Required for primary): Used for answer generation via `llama-3.1-8b-instant`.
* **Fallback Behavior**: If the Groq API fails or key is omitted, it falls back to a local Ollama instance (`llama3`).



\## Setup



```bash

cd section3\_generation

python -m venv venv

venv\\Scripts\\activate        # Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

copy .env.example .env

\# edit .env and set GROQ\_API\_KEY (get a free key at console.groq.com)

```



\*\*Never commit your real `.env` file or paste real API keys into code,

chat, or commit messages\*\* — treat any key that's been typed anywhere

outside your local `.env` as compromised and rotate it.



\## Run



```bash

python -m uvicorn app.main:app --reload --port 8002

```



Interactive API docs: http://localhost:8002/docs



Requires Section 1 (port 8000) and Section 2 (port 8001) to already be

running — Section 3 calls Section 2 over HTTP for retrieval.



\## Test it



```bash

curl -X POST http://localhost:8002/chat \\

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

&#x20; "answer": "According to the provided context, the Pro plan costs $8/month.",

&#x20; "is\_grounded": true,

&#x20; "groundedness\_reason": "Context sufficient for grounded response.",

&#x20; "llm\_provider": "Primary Groq (llama-3.1-8b-instant)",

&#x20; "sources": \[

&#x20;   { "document": "cloudsync\_test.md", "page": null, "section": "Pricing" }

&#x20; ],

&#x20; "suggested\_followups": \[

&#x20;   "Can you explain more details regarding how much does the pro plan cost?",

&#x20;   "What are the prerequisites or related configurations for this?",

&#x20;   "Are there any common troubleshooting steps for this topic?"

&#x20; ]

}

```



\## Environment variables (`.env`)



| Variable | Required | Default | Purpose |

|---|---|---|---|

| `GROQ\_API\_KEY` | Yes, for primary LLM | — | Groq API key (free tier available) |

| `PRIMARY\_LLM\_MODEL` | No | `llama-3.1-8b-instant` | Groq model name |

| `OLLAMA\_URL` | No | `http://localhost:11434/api/generate` | Local fallback LLM endpoint |

| `FALLBACK\_LLM\_MODEL` | No | `llama3` | Ollama model name |

| `RETRIEVAL\_SERVICE\_URL` | No | `http://127.0.0.1:8001` | Where Section 2 is running |



If `GROQ\_API\_KEY` is missing/invalid and no local Ollama server is

running at `OLLAMA\_URL`, the endpoint returns a clear

"unable to process your request" message rather than crashing.



\## Depends on



\- \*\*Section 2\*\* (`http://127.0.0.1:8001`) for retrieval — must be

&#x20; running before Section 3 starts, and restarted after any new

&#x20; document uploads to Section 1 (see Section 1 \& 2 READMEs for the

&#x20; caching limitation).



\## Architectural notes / trade-offs



\- \*\*Groundedness is score-based, not a second LLM call.\*\* A simple

&#x20; threshold on the retrieval similarity score decides whether to

&#x20; proceed to generation. This is fast and cheap, but coarser than

&#x20; using an LLM to judge relevance — a production version might use a

&#x20; lightweight classifier or a second LLM pass for higher precision.

\- \*\*Fallback LLM is local (Ollama).\*\* Chosen so a Groq outage doesn't

&#x20; take down answer generation entirely — genuinely independent

&#x20; infrastructure, not a second copy of the same dependency. Requires

&#x20; Ollama installed locally with the fallback model pulled

&#x20; (`ollama pull llama3`) for this path to actually work; if Ollama

&#x20; isn't running, the fallback attempt fails gracefully and returns the

&#x20; "unable to process" message instead of crashing.

\- \*\*Follow-up questions are template-based, not LLM-generated.\*\* Fast

&#x20; and free, but generic — the third suggestion ("common troubleshooting

&#x20; steps") is always the same regardless of topic. With more time, an

&#x20; LLM call could generate more contextually relevant follow-ups.

\- \*\*Sources only, no separate "Related Sections" field.\*\* The spec's

&#x20; example response format shows Sources and Related Pages/Sections as

&#x20; two separate fields; this implementation surfaces all retrieved

&#x20; chunks' locations under `sources` only. Documented here as a known

&#x20; gap rather than left silent.

