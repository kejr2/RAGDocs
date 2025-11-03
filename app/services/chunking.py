from typing import List
import uuid
from dataclasses import dataclass


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


def chunk_document(content: str, filename: str, doc_id: str) -> List[ChunkMetadata]:
    """
    Split document into chunks with metadata.
    Keeps document structure intact - doesn't separate code from text.
    """
    chunks = []
    lines = content.split('\n')
    
    current_chunk = []
    current_start = 0
    in_code_block = False
    code_language = None
    current_heading = None
    code_block_content = []
    
    for i, line in enumerate(lines):
        # Detect code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                # Start of code block
                in_code_block = True
                code_language = line.strip()[3:].strip() or "unknown"
                code_block_content = []
                # Track where code block starts
                code_block_start = i
            else:
                # End of code block - save as separate code chunk
                if code_block_content:
                    chunk_content = '\n'.join(code_block_content)
                    chunks.append(ChunkMetadata(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        source_file=filename,
                        content=chunk_content,
                        start=code_block_start,
                        end=i,
                        type="code",
                        heading=current_heading or "",
                        language=code_language
                    ))
                in_code_block = False
                code_language = None
                code_block_content = []
            continue
        
        # If inside code block, accumulate code lines
        if in_code_block:
            code_block_content.append(line)
            continue
        
        # Detect headings (only outside code blocks)
        if line.strip().startswith('#'):
            # Save previous text chunk if exists
            if current_chunk:
                chunk_content = '\n'.join(current_chunk)
                if chunk_content.strip():
                    chunks.append(ChunkMetadata(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        source_file=filename,
                        content=chunk_content,
                        start=current_start,
                        end=i - 1,
                        type="text",
                        heading=current_heading or "",
                        language=None
                    ))
            current_heading = line.strip()
            current_chunk = [line]
            current_start = i
        else:
            current_chunk.append(line)
        
        # Chunk by size (every 600 chars for text to keep context)
        if not in_code_block and len('\n'.join(current_chunk)) > 600:
            chunk_content = '\n'.join(current_chunk)
            if chunk_content.strip():
                chunks.append(ChunkMetadata(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_file=filename,
                    content=chunk_content,
                    start=current_start,
                    end=i,
                    type="text",
                    heading=current_heading or "",
                    language=None
                ))
            current_chunk = []
            current_start = i + 1
    
    # Save final chunk
    if current_chunk:
        chunk_content = '\n'.join(current_chunk)
        if chunk_content.strip():
            chunks.append(ChunkMetadata(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                source_file=filename,
                content=chunk_content,
                start=current_start,
                end=len(lines) - 1,
                type="text",
                heading=current_heading or "",
                language=None
            ))
    
    return chunks
