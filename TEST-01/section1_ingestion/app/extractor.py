"""
Extracts text from PDF, HTML, Markdown, and DOCX files.
Returns a list of {"text": ..., "page": ..., "section": ...} blocks
so downstream chunking/retrieval can preserve source attribution.
"""

import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("ingestion.extractor")


def extract_text(path: Path, ext: str) -> List[Dict]:
    if ext == ".pdf":
        return _extract_pdf(path)
    elif ext in (".html", ".htm"):
        return _extract_html(path)
    elif ext == ".md":
        return _extract_markdown(path)
    elif ext == ".docx":
        return _extract_docx(path)
    else:
        raise ValueError(f"Unsupported extension: {ext}")


def _extract_pdf(path: Path) -> List[Dict]:
    import pypdf

    blocks = []
    reader = pypdf.PdfReader(str(path))
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            blocks.append({"text": text, "page": page_num, "section": None})
    return blocks


def _extract_html(path: Path) -> List[Dict]:
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    soup = BeautifulSoup(raw, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    blocks = []
    current_section = None
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "th", "blockquote", "pre"]):
        text = tag.get_text(strip=True)
        if not text:
            continue
        if tag.name in ("h1", "h2", "h3"):
            current_section = text
            continue
        blocks.append({"text": text, "page": None, "section": current_section})

    if blocks:
        return blocks

    logger.warning(
        f"No structured tags (p/li/h1-3/td/etc) found in {path.name}; "
        f"falling back to whole-page text extraction."
    )
    full_text = soup.get_text(separator="\n", strip=True)
    full_text = "\n".join(line for line in full_text.split("\n") if line.strip())

    if full_text:
        return [{"text": full_text, "page": None, "section": None}]

    return []


def _extract_markdown(path: Path) -> List[Dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    blocks = []
    current_section = None
    current_lines = []

    def flush():
        if current_lines:
            text = "\n".join(current_lines).strip()
            if text:
                blocks.append({"text": text, "page": None, "section": current_section})

    for line in content.split("\n"):
        if line.startswith("#"):
            flush()
            current_lines = []
            current_section = line.lstrip("#").strip()
        else:
            current_lines.append(line)
    flush()
    return blocks


def _extract_docx(path: Path) -> List[Dict]:
    import docx

    doc = docx.Document(str(path))
    blocks = []
    current_section = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if para.style.name.startswith("Heading"):
            current_section = text
            continue
        blocks.append({"text": text, "page": None, "section": current_section})
    return blocks
