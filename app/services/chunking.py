"""
Markdown-aware document chunking with enriched metadata.

Uses MarkdownTextSplitter (chunk_size=600, chunk_overlap=200) so that section
boundaries are respected and table / list structures are not split mid-row.
Callouts (Note / Warning / Important) are tagged inline before splitting so
the [WARNING] / [IMPORTANT NOTE] marker survives chunking (Issue 3).
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
# Callout detection (Issue 3)
# ---------------------------------------------------------------------------
# Detect callout / admonition blocks in the source document and prefix their
# content with [IMPORTANT NOTE] or [WARNING] so the marker survives chunking
# and embedding. The prefix is inlined into the source BEFORE splitting so the
# callout text stays attached to its parent section in whichever chunk it
# falls into. Increased overlap (200 tokens) further reduces the chance of a
# callout straddling a boundary and getting orphaned.

_WARNING_KEYWORDS = ("warning", "danger", "caution", "critical")
_NOTE_KEYWORDS    = ("note", "important", "tip", "info")

_CALLOUT_LINE_RE = re.compile(
    r"""(?ix)
    ^(?P<indent>\s*)
    (?:>\s*)?                       # optional blockquote marker
    (?:[\u26A0\u2757\U0001F4CC\u2139\u2705]\uFE0F?\s*)?  # optional emoji
    (?:\*{1,2})?                    # optional bold start
    (?P<word>warning|danger|caution|critical|note|important|tip|info)
    (?:\*{1,2})?                    # optional bold end
    \s*[:\-—]                       # required punctuation
    (?P<rest>.*)$
    """
)


def _tag_callouts(content: str) -> str:
    """
    Walk *content* line by line. When a line opens a callout (e.g.
    "> **Warning:** ..."), prefix that line and all immediately-following
    indented / blockquote-continuation lines with [WARNING] or
    [IMPORTANT NOTE]. Idempotent — already-tagged callouts are skipped.
    """
    out_lines: List[str] = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _CALLOUT_LINE_RE.match(line)
        if not m or "[WARNING]" in line or "[IMPORTANT NOTE]" in line:
            out_lines.append(line)
            i += 1
            continue

        word = m.group("word").lower()
        tag  = "[WARNING]" if word in _WARNING_KEYWORDS else "[IMPORTANT NOTE]"
        indent = m.group("indent") or ""

        # Insert the tag at the start of the line (after indent) and inline
        # the rest of the callout block — subsequent blockquote / indented
        # continuation lines belong to the same callout.
        first = f"{indent}{tag} {line[len(indent):].lstrip()}"
        out_lines.append(first)
        i += 1
        while i < len(lines):
            nxt = lines[i]
            stripped = nxt.lstrip()
            # Continuation: blockquote line, or indented under the callout,
            # or a non-blank line right after with no new heading / fence.
            is_blockquote_cont = stripped.startswith(">")
            is_indent_cont = nxt.startswith(indent + " ") and stripped != ""
            is_blank = not stripped
            if is_blockquote_cont or is_indent_cont:
                out_lines.append(nxt)
                i += 1
                continue
            if is_blank:
                out_lines.append(nxt)
                i += 1
                # Stop after one blank line so we don't swallow the next paragraph
                break
            break
    return "\n".join(out_lines)


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
        splitter = MarkdownTextSplitter(chunk_size=600, chunk_overlap=200)
    except ImportError:
        try:
            from langchain.text_splitter import MarkdownTextSplitter
            splitter = MarkdownTextSplitter(chunk_size=600, chunk_overlap=200)
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=600, chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

    # Issue 3: tag callouts ([WARNING] / [IMPORTANT NOTE]) inline so they
    # survive splitting and stay attached to their parent section.
    content = _tag_callouts(content)

    headings = _extract_headings(content)
    raw_chunks = splitter.split_text(content)

    chunks: List[ChunkMetadata] = []
    search_pos = 0

    for chunk_text in raw_chunks:
        if not chunk_text.strip():
            continue

        # Locate chunk inside the original text (account for overlap window)
        fragment = chunk_text[:80] if len(chunk_text) >= 80 else chunk_text
        start_hint = max(0, search_pos - 200)
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
        search_pos = pos + max(len(chunk_text) - 200, 1)

    # Sort by position in original document
    chunks.sort(key=lambda c: c.start)
    return chunks
