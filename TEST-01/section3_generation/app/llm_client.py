import os
import logging
import httpx
import openai
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful documentation assistant.
Answer the user's question strictly grounded on the provided source contexts.
If the provided context does not contain enough information to answer, respond ONLY with:
"This information is not available in the provided documentation."
Do not invent information outside of the provided context.
Do not offer general knowledge, inferred answers, or "related" information as a substitute when the exact answer is missing.
"""

class LLMClient:
    def __init__(self):
        self.openai_client = openai.OpenAI(
            # 👇 PASTE YOUR ACTUAL GROQ KEY HERE (Inside quotes)
            api_key=os.getenv("GROQ_API_KEY", "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"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.primary_model = os.getenv("PRIMARY_LLM_MODEL", "llama-3.1-8b-instant")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.fallback_model = os.getenv("FALLBACK_LLM_MODEL", "llama3")

    async def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> Tuple[str, str]:
        context_str = "\n\n---\n\n".join(
            [f"Source: {c['metadata'].get('document_name', 'Unknown')}\nText: {c['text']}" for c in context_chunks]
        )
        
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {query}"

        # 1. Primary Path: Groq API (using OpenAI client format)
        # 👇 FIX: Checking if key is present on self.openai_client
        if self.openai_client.api_key and "gsk_" in self.openai_client.api_key:
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.primary_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                answer = response.choices[0].message.content
                return answer, f"Primary Groq ({self.primary_model})"
            except Exception as e:
                logger.warning(f"[FALLBACK TRIGGERED] Primary LLM failed: {e}. Switching to fallback LLM.")

        # 2. Fallback Path: Local Ollama Model
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": self.fallback_model,
                    "prompt": f"{SYSTEM_PROMPT}\n\n{user_prompt}",
                    "stream": False
                }
                res = await client.post(self.ollama_url, json=payload, timeout=30.0)
                if res.status_code == 200:
                    answer = res.json().get("response", "")
                    return answer, f"Fallback ({self.fallback_model} via Ollama)"
        except Exception as local_err:
            logger.error(f"Fallback LLM also failed: {local_err}")

        return "I am unable to process your request at this time due to an upstream LLM service outage.", "none"