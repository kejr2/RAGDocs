"""
Document processors.

PDFProcessor  — uses pymupdf4llm for Markdown-preserving extraction (Fix 1),
                with pypdf fallback if the library is not installed.
HTMLProcessor — uses BeautifulSoup to produce Markdown-ish text.
DocumentProcessor — advanced LangChain-based processor (not yet wired to API).

All processors delegate to chunk_document() which uses MarkdownTextSplitter
and returns ChunkMetadata objects carrying the enriched metadata fields
(page_number, section_heading, has_table, has_list).
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import re
import uuid
from dataclasses import dataclass

from app.services.chunking import chunk_document


# ---------------------------------------------------------------------------
# Chunk dataclass used by DocumentProcessor (mirrors ChunkMetadata)
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
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
# DocumentProcessor (advanced, Markdown-aware — for future wiring)
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """Advanced document processor using LangChain text splitters."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\nclass ", "\ndef ", "\n\t", "\n", " ", ""]
        )

    def extract_code_blocks(self, content: str) -> List[Dict]:
        code_blocks = []
        for match in re.finditer(r'```(\w+)?\n(.*?)```', content, re.DOTALL):
            code_blocks.append({
                'content': match.group(2).strip(),
                'language': match.group(1) or "unknown",
                'start': match.start(),
                'end': match.end(),
            })
        return code_blocks

    def extract_headings(self, content: str) -> List[Dict]:
        headings = []
        position = 0
        for line in content.split('\n'):
            if line.strip().startswith('#'):
                headings.append({
                    'text': line.strip(),
                    'position': position,
                    'level': len(line) - len(line.lstrip('#')),
                })
            position += len(line) + 1
        return headings

    def get_current_heading(self, position: int, headings: List[Dict]) -> str:
        current = ""
        for h in headings:
            if h['position'] <= position:
                current = h['text']
            else:
                break
        return current

    def process_document(self, content: str, filename: str, doc_id: str) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        code_blocks = sorted(self.extract_code_blocks(content), key=lambda x: x['start'])
        headings = self.extract_headings(content)
        processed_regions = []

        for block in code_blocks:
            sub = self.code_splitter.split_text(block['content']) if len(block['content']) > 800 else [block['content']]
            for chunk_content in sub:
                all_chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()), doc_id=doc_id, source_file=filename,
                    content=chunk_content, start=block['start'], end=block['end'],
                    type="code", heading=self.get_current_heading(block['start'], headings),
                    language=block['language'],
                ))
            processed_regions.append((block['start'], block['end']))

        text_content = content
        for start, end in sorted(processed_regions, reverse=True):
            text_content = text_content[:start] + text_content[end:]

        if text_content.strip():
            current_pos = 0
            for chunk_content in self.text_splitter.split_text(text_content):
                chunk_start = content.find(chunk_content, current_pos)
                if chunk_start == -1:
                    chunk_start = current_pos
                all_chunks.append(Chunk(
                    chunk_id=str(uuid.uuid4()), doc_id=doc_id, source_file=filename,
                    content=chunk_content, start=chunk_start,
                    end=chunk_start + len(chunk_content), type="text",
                    heading=self.get_current_heading(chunk_start, headings),
                    language="",
                ))
                current_pos = chunk_start + len(chunk_content)

        all_chunks.sort(key=lambda x: x.start)
        return all_chunks


# ---------------------------------------------------------------------------
# PDFProcessor  (Fix 1 — pymupdf4llm for Markdown-preserving extraction)
# ---------------------------------------------------------------------------

class PDFProcessor:
    """
    Extract text from PDFs as Markdown via pymupdf4llm, then chunk with
    MarkdownTextSplitter.  Falls back to pypdf raw text if pymupdf4llm is
    unavailable (e.g. inside Docker before requirements update).
    """

    def process_pdf(self, pdf_content: bytes, filename: str, doc_id: str) -> List:
        """Return List[ChunkMetadata] for the given PDF bytes."""
        try:
            import fitz          # PyMuPDF
            import pymupdf4llm
        except ImportError:
            return self._process_pdf_pypdf_fallback(pdf_content, filename, doc_id)

        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_data = pymupdf4llm.to_markdown(doc, page_chunks=True)

            if not page_data:
                raise ValueError("pymupdf4llm returned no content — trying fallback")

            all_chunks = []
            for item in page_data:
                if isinstance(item, dict):
                    page_text = item.get("text", "")
                    meta = item.get("metadata", {})
                    # page is 0-indexed in pymupdf4llm
                    raw_page = meta.get("page", 0) if isinstance(meta, dict) else 0
                    page_num = (raw_page + 1) if isinstance(raw_page, int) else 1
                else:
                    page_text = str(item)
                    page_num = 1

                if not page_text.strip():
                    continue

                page_chunks = chunk_document(
                    page_text, filename, doc_id, page_number=page_num
                )
                all_chunks.extend(page_chunks)

            if not all_chunks:
                raise ValueError("No chunks produced — trying fallback")

            return all_chunks

        except Exception as exc:
            # Surface as a proper error (caller can catch and serve 500)
            raise Exception(f"Error processing PDF: {exc}") from exc

    # ------------------------------------------------------------------
    def _process_pdf_pypdf_fallback(
        self, pdf_content: bytes, filename: str, doc_id: str
    ) -> List:
        """Fallback: use pypdf (raw text, no table structure)."""
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(pdf_content))
            text_content = ""
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n\n--- Page {page_num} ---\n\n{page_text}"

            if not text_content.strip():
                raise Exception(
                    "No text could be extracted from PDF.  "
                    "The PDF might be scanned/image-based."
                )
            return chunk_document(text_content, filename, doc_id)
        except Exception as exc:
            raise Exception(f"Error processing PDF: {exc}") from exc


# ---------------------------------------------------------------------------
# HTMLProcessor
# ---------------------------------------------------------------------------

class HTMLProcessor:
    """Processor for HTML documents."""

    def process_html(self, html_content: str, filename: str, doc_id: str) -> List:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text_content = ""
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                level = int(heading.name[1])
                text_content += f"\n{'#' * level} {heading.get_text().strip()}\n\n"

            for element in soup.find_all(['p', 'pre', 'code', 'blockquote', 'li']):
                text = element.get_text().strip()
                if text:
                    if element.name in ['pre', 'code']:
                        text_content += f"\n```\n{text}\n```\n\n"
                    else:
                        text_content += f"{text}\n\n"

            if len(text_content) < 100:
                text_content = soup.get_text()

            lines = (line.strip() for line in text_content.splitlines())
            text_content = '\n'.join(line for line in lines if line)

            return chunk_document(text_content, filename, doc_id)
        except Exception as exc:
            raise Exception(f"Error processing HTML: {exc}") from exc
