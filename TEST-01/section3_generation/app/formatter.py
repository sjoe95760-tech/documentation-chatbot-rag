from typing import List, Dict, Any

class ResponseFormatter:
    def format_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        seen = set()

        for c in chunks:
            meta = c.get("metadata", {})
            doc_name = meta.get("document_name", meta.get("source", "Unknown Document"))
            page = meta.get("page_number", meta.get("page", None))
            section = meta.get("section_heading", meta.get("heading", None))

            key = (doc_name, page, section)
            if key not in seen:
                seen.add(key)
                sources.append({
                    "document": doc_name,
                    "page": page,
                    "section": section
                })
        return sources

    def generate_followup_questions(self, query: str) -> List[str]:
        return [
            f"Can you explain more details regarding {query.lower().replace('?', '')}?",
            "What are the prerequisites or related configurations for this?",
            "Are there any common troubleshooting steps for this topic?"
        ]