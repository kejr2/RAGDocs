"""
Markdown-aware document chunking with enriched metadata.

Uses MarkdownTextSplitter (chunk_size=600, chunk_overlap=150) so that section
boundaries are respected and table / list structures are not split mid-row.
Extra metadata carried per chunk: page_number, section_heading, has_table,
has_list — used later for BM25 hybrid retrieval and section-filtered fallback.
"""
from typing import List
import uuid
import re
from dataclasses import dataclass, field


@dataclass
class ChunkMetadata:
    chunk_id: str
    doc_id: str
    source_file: str
    content: str
    start: int
    end: int
    type: str
    heading: str = ""
    language: str = ""
    # enriched metadata (Fix 3)
    page_number: int = 0
    section_heading: str = ""
    has_table: bool = False
    has_list: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_headings(content: str) -> list:
    """Return list of {text, position} for every Markdown heading."""
    headings = []
    for m in re.finditer(r'^#{1,6}\s+(.+)$', content, re.MULTILINE):
        headings.append({"text": m.group(0).strip(), "position": m.start()})
    return headings


def _get_current_heading(position: int, headings: list) -> str:
    """Return the most recent heading whose start is <= *position*."""
    current = ""
    for h in headings:
        if h["position"] <= position:
            current = h["text"]
        else:
            break
    return current


def _is_predominantly_code(text: str) -> bool:
    """
    Return True only when the majority of non-blank lines in *text* are inside
    fenced code blocks (``` … ```).  Chunks where ``` is merely a formatting
    artefact from pymupdf4llm wrapping prose text are classified as "text".
    """
    inside = False
    code_lines = 0
    text_lines = 0
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if not line.strip():
            continue
        if inside:
            code_lines += 1
        else:
            text_lines += 1
    total = code_lines + text_lines
    if total == 0:
        return False
    return code_lines / total > 0.5


def _has_table(text: str) -> bool:
    """True when *text* contains at least one Markdown table row (| … |)."""
    return bool(re.search(r'^\|.+\|', text, re.MULTILINE))


def _has_list(text: str) -> bool:
    """True when *text* contains at least one Markdown bullet / ordered list item."""
    return bool(re.search(r'^(\s*[-*+]|\s*\d+\.)\s+', text, re.MULTILINE))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_document(
    content: str,
    filename: str,
    doc_id: str,
    page_number: int = 0,
) -> List[ChunkMetadata]:
    """
    Split *content* into overlapping chunks using MarkdownTextSplitter.

    Parameters
    ----------
    content      : Raw (Markdown-formatted) document text.
    filename     : Original file name — stored in metadata.
    doc_id       : Document identifier.
    page_number  : PDF page number (1-indexed).  Pass 0 for non-PDF sources.

    Returns
    -------
    List of ChunkMetadata objects sorted by start position.
    """
    # Build splitter — prefer MarkdownTextSplitter, fall back gracefully
    try:
        from langchain_text_splitters import MarkdownTextSplitter
        splitter = MarkdownTextSplitter(chunk_size=600, chunk_overlap=150)
    except ImportError:
        try:
            from langchain.text_splitter import MarkdownTextSplitter
            splitter = MarkdownTextSplitter(chunk_size=600, chunk_overlap=150)
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=600, chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

    headings = _extract_headings(content)
    raw_chunks = splitter.split_text(content)

    chunks: List[ChunkMetadata] = []
    search_pos = 0

    for chunk_text in raw_chunks:
        if not chunk_text.strip():
            continue

        # Locate chunk inside the original text (account for overlap window)
        fragment = chunk_text[:80] if len(chunk_text) >= 80 else chunk_text
        start_hint = max(0, search_pos - 150)
        pos = content.find(fragment, start_hint)
        if pos == -1:
            # Fallback: search without offset
            pos = content.find(fragment)
        if pos == -1:
            pos = search_pos

        sec_heading = _get_current_heading(pos, headings)
        has_tbl = _has_table(chunk_text)
        has_lst = _has_list(chunk_text)

        # A chunk is "code" only when the majority of its non-blank lines live
        # inside fenced ``` blocks.  pymupdf4llm sometimes wraps prose text in
        # a ``` block to preserve indentation; we don't want those classified
        # as code so text-embedding queries can reach them.
        stripped = chunk_text.strip()
        chunk_type = "code" if _is_predominantly_code(stripped) else "text"
        language = ""
        if chunk_type == "code":
            first_line = stripped.split("\n")[0]
            language = first_line[3:].strip() if first_line.startswith("```") else ""

        chunks.append(ChunkMetadata(
            chunk_id=str(uuid.uuid4()),
            doc_id=doc_id,
            source_file=filename,
            content=chunk_text,
            start=pos,
            end=pos + len(chunk_text),
            type=chunk_type,
            heading=sec_heading,
            language=language,
            page_number=page_number,
            section_heading=sec_heading,
            has_table=has_tbl,
            has_list=has_lst,
        ))

        # Advance search cursor, keeping overlap window
        search_pos = pos + max(len(chunk_text) - 150, 1)

    # Sort by position in original document
    chunks.sort(key=lambda c: c.start)
    return chunks
