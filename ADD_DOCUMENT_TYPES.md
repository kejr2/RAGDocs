# Quick Guide: Adding Document Type Support

## Current State

**What works now:**
- ✅ Text files (`.txt`, `.md`, `.markdown`)
- ✅ Code files (`.py`, `.js`, etc.) - treated as text

**What exists but isn't used:**
- ⚠️ `PDFProcessor` class exists in `app/services/processing.py`
- ⚠️ `HTMLProcessor` class exists in `app/services/processing.py`

**Current upload logic:**
- Just tries to decode everything as UTF-8 text
- No file type detection
- No routing to special processors

---

## Quick Win: Enable PDF and HTML Support

The processors already exist! Just update `app/api/docs.py`:

### Change This (line 42-46):
```python
# Try to decode as text
try:
    text_content = content.decode('utf-8')
except:
    text_content = content.decode('utf-8', errors='ignore')
```

### To This:
```python
import os
from app.services.processing import PDFProcessor, HTMLProcessor

# Detect file type
file_ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''

# Process based on type
if file_ext == '.pdf':
    processor = PDFProcessor()
    chunks = processor.process_pdf(content, filename, "")
elif file_ext in ['.html', '.htm']:
    processor = HTMLProcessor()
    try:
        text_content = content.decode('utf-8')
    except:
        text_content = content.decode('utf-8', errors='ignore')
    chunks = processor.process_html(text_content, filename, "")
else:
    # Default: text processing
    try:
        text_content = content.decode('utf-8')
    except:
        text_content = content.decode('utf-8', errors='ignore')
    chunks = chunk_document(text_content, filename, doc_id)
```

### Then Fix Doc ID Generation:
```python
# Move doc_id generation before processing
doc_id = hashlib.md5(content).hexdigest()  # Use raw content

# Update chunks with doc_id
for chunk in chunks:
    chunk.doc_id = doc_id
```

---

## Adding More Document Types

### Step 1: Add Libraries to `requirements.txt`

```txt
# Word documents
python-docx>=1.0.0

# Excel files  
openpyxl>=3.1.0
pandas>=2.0.0

# PowerPoint
python-pptx>=0.6.21

# JSON/YAML (usually already available)
pyyaml>=6.0
```

### Step 2: Create Processors

Add to `app/services/processing.py` or create `app/services/document_processors.py`:

```python
class DOCXProcessor:
    """Processor for Word documents"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor()  # Use existing chunking
    
    def process_docx(self, docx_content: bytes, filename: str, doc_id: str) -> List[Chunk]:
        try:
            from docx import Document
            from io import BytesIO
            
            doc = Document(BytesIO(docx_content))
            text_content = ""
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n\n"
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    text_content += " | ".join(cell.text for cell in row.cells) + "\n"
                text_content += "\n"
            
            return self.doc_processor.process_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing DOCX: {str(e)}")
```

### Step 3: Update Upload Endpoint

Add to the file type detection in `app/api/docs.py`:

```python
elif file_ext == '.docx':
    from app.services.processing import DOCXProcessor
    processor = DOCXProcessor()
    chunks = processor.process_docx(content, filename, "")
```

---

## Recommended Implementation Order

1. **PDF** - Already has processor, just needs routing ✅
2. **HTML** - Already has processor, just needs routing ✅  
3. **DOCX** - Very common, good libraries available
4. **XLSX** - Common for documentation
5. **JSON/YAML** - Often in API docs
6. **PPTX** - Presentation docs

---

## File Type Detection

You can detect by:
- **File extension** (most reliable)
- **MIME type** (if provided by client)
- **Magic bytes** (file signature checking)

Current approach uses file extension which is simplest.

---

## Testing

After adding support:

```bash
# Test PDF
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@sample.pdf"

# Test Word
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@document.docx"
```

---

## Complete Example: Adding DOCX Support

**1. Add to requirements.txt:**
```
python-docx>=1.0.0
```

**2. Add processor to `app/services/processing.py`:**
```python
class DOCXProcessor:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
    
    def process_docx(self, docx_content: bytes, filename: str, doc_id: str) -> List[Chunk]:
        from docx import Document
        from io import BytesIO
        
        doc = Document(BytesIO(docx_content))
        text_content = ""
        
        for para in doc.paragraphs:
            text_content += para.text + "\n\n"
        
        return self.doc_processor.process_document(text_content, filename, doc_id)
```

**3. Update `app/api/docs.py` upload function:**
```python
# After reading content
file_ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''

if file_ext == '.docx':
    from app.services.processing import DOCXProcessor
    processor = DOCXProcessor()
    chunks = processor.process_docx(content, filename, doc_id)
elif file_ext == '.pdf':
    from app.services.processing import PDFProcessor
    processor = PDFProcessor()
    chunks = processor.process_pdf(content, filename, doc_id)
elif file_ext in ['.html', '.htm']:
    from app.services.processing import HTMLProcessor
    processor = HTMLProcessor()
    text_content = content.decode('utf-8', errors='ignore')
    chunks = processor.process_html(text_content, filename, doc_id)
else:
    # Default text processing
    text_content = content.decode('utf-8', errors='ignore')
    chunks = chunk_document(text_content, filename, doc_id)
```

**4. Rebuild:**
```bash
docker compose build backend
docker compose up -d backend
```

That's it! The chunking, embedding, and storage logic stays the same.

