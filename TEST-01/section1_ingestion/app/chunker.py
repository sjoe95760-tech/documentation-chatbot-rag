"""
Splits extracted text blocks into overlapping chunks sized for embedding.
Keeps page/section metadata attached to every chunk for source attribution.
"""

from typing import List, Dict

CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 150    # overlap between consecutive chunks


def chunk_text(blocks: List[Dict], doc_name: str) -> List[Dict]:
    chunks = []

    for block in blocks:
        text = block["text"]
        page = block.get("page")
        section = block.get("section")

        if len(text) <= CHUNK_SIZE:
            chunks.append({"text": text, "page": page, "section": section})
            continue

        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            piece = text[start:end].strip()
            if piece:
                chunks.append({"text": piece, "page": page, "section": section})
            start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks
