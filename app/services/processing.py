from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import re
import uuid
from dataclasses import dataclass


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


class DocumentProcessor:
    """Advanced document processor using LangChain text splitters"""
    
    def __init__(self):
        # Text splitter for general content
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Code splitter with different settings
        self.code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\nclass ", "\ndef ", "\n\t", "\n", " ", ""]
        )
    
    def extract_code_blocks(self, content: str) -> List[Dict]:
        """Extract code blocks from markdown/text."""
        code_blocks = []
        pattern = r'```(\w+)?\n(.*?)```'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or "unknown"
            code = match.group(2)
            start = match.start()
            end = match.end()
            
            code_blocks.append({
                'content': code.strip(),
                'language': language,
                'start': start,
                'end': end
            })
        
        return code_blocks
    
    def extract_headings(self, content: str) -> List[Dict]:
        """Extract markdown headings with positions."""
        headings = []
        lines = content.split('\n')
        position = 0
        
        for line in lines:
            if line.strip().startswith('#'):
                headings.append({
                    'text': line.strip(),
                    'position': position,
                    'level': len(line) - len(line.lstrip('#'))
                })
            position += len(line) + 1
        
        return headings
    
    def get_current_heading(self, position: int, headings: List[Dict]) -> str:
        """Find the most recent heading before a position."""
        current_heading = ""
        for heading in headings:
            if heading['position'] <= position:
                current_heading = heading['text']
            else:
                break
        return current_heading
    
    def process_document(self, content: str, filename: str, doc_id: str) -> List[Chunk]:
        """
        Process document into chunks with proper metadata.
        Handles both text and code separately.
        """
        all_chunks = []
        
        # Extract structure
        code_blocks = self.extract_code_blocks(content)
        headings = self.extract_headings(content)
        
        # Sort code blocks by position
        code_blocks.sort(key=lambda x: x['start'])
        
        # Track processed regions
        processed_regions = []
        
        # Process code blocks
        for block in code_blocks:
            # Split large code blocks
            if len(block['content']) > 800:
                code_chunks = self.code_splitter.split_text(block['content'])
            else:
                code_chunks = [block['content']]
            
            for i, chunk_content in enumerate(code_chunks):
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_file=filename,
                    content=chunk_content,
                    start=block['start'],
                    end=block['end'],
                    type="code",
                    heading=self.get_current_heading(block['start'], headings),
                    language=block['language']
                )
                all_chunks.append(chunk)
            
            processed_regions.append((block['start'], block['end']))
        
        # Extract text content (excluding code blocks)
        text_content = content
        for start, end in sorted(processed_regions, reverse=True):
            text_content = text_content[:start] + text_content[end:]
        
        # Process text content
        if text_content.strip():
            text_chunks = self.text_splitter.split_text(text_content)
            
            # Calculate approximate positions for text chunks
            current_pos = 0
            for chunk_content in text_chunks:
                # Find this chunk in original content
                chunk_start = content.find(chunk_content, current_pos)
                if chunk_start == -1:
                    chunk_start = current_pos
                
                chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_file=filename,
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_start + len(chunk_content),
                    type="text",
                    heading=self.get_current_heading(chunk_start, headings),
                    language=""
                )
                all_chunks.append(chunk)
                current_pos = chunk_start + len(chunk_content)
        
        # Sort chunks by start position
        all_chunks.sort(key=lambda x: x.start)
        
        return all_chunks


class PDFProcessor:
    """Processor for PDF documents."""
    
    def __init__(self):
        from app.services.chunking import chunk_document
        self.chunk_document = chunk_document
    
    def process_pdf(self, pdf_content: bytes, filename: str, doc_id: str) -> List:
        """Extract text from PDF and process it."""
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
                raise Exception("No text could be extracted from PDF. The PDF might be scanned/image-based.")
            
            # Use simple chunking logic (matches current implementation)
            return self.chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")


class HTMLProcessor:
    """Processor for HTML documents."""
    
    def __init__(self):
        from app.services.chunking import chunk_document
        self.chunk_document = chunk_document
    
    def process_html(self, html_content: str, filename: str, doc_id: str) -> List:
        """Extract text from HTML and process it."""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract text with structure
            text_content = ""
            
            # Preserve headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                level = int(heading.name[1])
                text_content += f"\n{'#' * level} {heading.get_text().strip()}\n\n"
            
            # Extract paragraphs and code blocks
            for element in soup.find_all(['p', 'pre', 'code', 'blockquote', 'li']):
                text = element.get_text().strip()
                if text:
                    if element.name in ['pre', 'code']:
                        # Preserve code blocks
                        text_content += f"\n```\n{text}\n```\n\n"
                    else:
                        text_content += f"{text}\n\n"
            
            # Fallback: get all text if structure extraction didn't work well
            if len(text_content) < 100:
                text_content = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            text_content = '\n'.join(line for line in lines if line)
            
            # Use simple chunking logic (matches current implementation)
            return self.chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing HTML: {str(e)}")

