# Guide: Adding Support for Different Document Types

## Current Support

**Currently Supported:**
- ✅ Markdown files (`.md`)
- ✅ Plain text files (`.txt`)
- ✅ Code files (`.py`, `.js`, `.ts`, etc.) - as text
- ✅ Any UTF-8 text file

**Processors Available (Not Integrated):**
- ⚠️ `PDFProcessor` - exists in `app/services/processing.py` but not used
- ⚠️ `HTMLProcessor` - exists in `app/services/processing.py` but not used

## How to Add More Document Type Support

### Architecture Overview

The current upload flow:
1. Read file content as bytes
2. Try to decode as UTF-8 text
3. Use `chunk_document()` to chunk the text

**To add new document types, you need to:**
1. Create a processor class
2. Detect file type from extension/MIME type
3. Route to appropriate processor
4. All processors should return text that can be chunked

---

## Step-by-Step Guide

### Step 1: Add Required Libraries

Add to `requirements.txt`:

```txt
# For PDF support (already installed)
pypdf==4.0.1

# For Word documents
python-docx>=1.0.0

# For Excel files
openpyxl>=3.1.0
pandas>=2.0.0

# For PowerPoint
python-pptx>=0.6.21

# For HTML/XML (already installed)
beautifulsoup4==4.12.2
lxml>=4.9.0

# For JSON/YAML
pyyaml>=6.0  # Already in dependencies

# For image OCR (optional)
pytesseract>=0.3.10
Pillow>=10.0.0

# For EPUB books
ebooklib>=0.18
```

### Step 2: Create Document Processor Service

Create `app/services/document_processors.py`:

```python
from typing import List, Optional
from app.services.chunking import chunk_document, ChunkMetadata
import os


class DocumentProcessorRegistry:
    """Registry for document type processors"""
    
    def __init__(self):
        self.processors = {}
        self._register_default_processors()
    
    def _register_default_processors(self):
        """Register default processors"""
        # Text processors
        self.processors['.txt'] = self._process_text
        self.processors['.md'] = self._process_text
        self.processors['.markdown'] = self._process_text
        
        # Code files (process as text with language detection)
        self.processors['.py'] = self._process_code_file
        self.processors['.js'] = self._process_code_file
        self.processors['.ts'] = self._process_code_file
        self.processors['.java'] = self._process_code_file
        self.processors['.cpp'] = self._process_code_file
        self.processors['.c'] = self._process_code_file
        self.processors['.go'] = self._process_code_file
        self.processors['.rs'] = self._process_code_file
        self.processors['.rb'] = self._process_code_file
        self.processors['.php'] = self._process_code_file
        
        # PDF
        self.processors['.pdf'] = self._process_pdf
        
        # HTML
        self.processors['.html'] = self._process_html
        self.processors['.htm'] = self._process_html
        
        # Word documents
        self.processors['.docx'] = self._process_docx
        self.processors['.doc'] = self._process_doc  # Requires libreoffice
        
        # Excel
        self.processors['.xlsx'] = self._process_excel
        self.processors['.xls'] = self._process_excel
        
        # PowerPoint
        self.processors['.pptx'] = self._process_pptx
        
        # Data files
        self.processors['.json'] = self._process_json
        self.processors['.yaml'] = self._process_yaml
        self.processors['.yml'] = self._process_yaml
        self.processors['.xml'] = self._process_xml
        self.processors['.csv'] = self._process_csv
        
        # Markdown variants
        self.processors['.rst'] = self._process_text  # reStructuredText
        self.processors['.adoc'] = self._process_text  # AsciiDoc
    
    def get_processor(self, file_extension: str):
        """Get processor for file extension"""
        ext = file_extension.lower()
        return self.processors.get(ext, self._process_text)  # Default to text
    
    def _process_text(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process plain text files"""
        try:
            text_content = content.decode('utf-8')
        except:
            text_content = content.decode('utf-8', errors='ignore')
        return chunk_document(text_content, filename, doc_id)
    
    def _process_code_file(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process code files - detect language from extension"""
        try:
            text_content = content.decode('utf-8')
        except:
            text_content = content.decode('utf-8', errors='ignore')
        
        # Language detection from extension
        ext = os.path.splitext(filename)[1].lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c',
            '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php'
        }
        detected_lang = lang_map.get(ext, 'unknown')
        
        # For code files, treat entire file as code chunk
        chunks = chunk_document(text_content, filename, doc_id)
        # Mark chunks as code if they're mostly code
        for chunk in chunks:
            if chunk.type == "text" and len(text_content) > 100:
                # If file is mostly code patterns, mark as code
                code_indicators = ['def ', 'class ', 'function ', 'import ', 'const ', 'var ', 'let ']
                if any(indicator in chunk.content for indicator in code_indicators):
                    chunk.type = "code"
                    chunk.language = detected_lang
        
        return chunks
    
    def _process_pdf(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process PDF files"""
        try:
            from pypdf import PdfReader
            from io import BytesIO
            
            reader = PdfReader(BytesIO(content))
            text_content = ""
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n\n--- Page {page_num} ---\n\n"
                    text_content += page_text
            
            if not text_content.strip():
                raise Exception("No text could be extracted from PDF")
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")
    
    def _process_html(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process HTML files"""
        try:
            from bs4 import BeautifulSoup
            
            # Try UTF-8 first, then fallback
            try:
                html_content = content.decode('utf-8')
            except:
                html_content = content.decode('utf-8', errors='ignore')
            
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
            for element in soup.find_all(['p', 'pre', 'code', 'blockquote']):
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
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing HTML: {str(e)}")
    
    def _process_docx(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process Word documents (.docx)"""
        try:
            from docx import Document
            from io import BytesIO
            
            doc = Document(BytesIO(content))
            text_content = ""
            
            # Extract text with structure
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    # Check if it's a heading
                    if paragraph.style.name.startswith('Heading'):
                        level = paragraph.style.name.split()[-1] if paragraph.style.name.split()[-1].isdigit() else '1'
                        try:
                            level_num = int(level)
                            text_content += f"\n{'#' * level_num} {text}\n\n"
                        except:
                            text_content += f"\n## {text}\n\n"
                    else:
                        text_content += f"{text}\n\n"
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = ' | '.join(cell.text.strip() for cell in row.cells)
                    text_content += f"{row_text}\n"
                text_content += "\n"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing DOCX: {str(e)}")
    
    def _process_excel(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process Excel files"""
        try:
            import pandas as pd
            from io import BytesIO
            
            # Try reading as Excel
            excel_file = pd.ExcelFile(BytesIO(content))
            text_content = ""
            
            for sheet_name in excel_file.sheet_names:
                text_content += f"\n\n## Sheet: {sheet_name}\n\n"
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Convert to markdown table
                text_content += df.to_markdown(index=False)
                text_content += "\n\n"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing Excel: {str(e)}")
    
    def _process_pptx(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process PowerPoint files"""
        try:
            from pptx import Presentation
            from io import BytesIO
            
            prs = Presentation(BytesIO(content))
            text_content = ""
            
            for slide_num, slide in enumerate(prs.slides, 1):
                text_content += f"\n\n--- Slide {slide_num} ---\n\n"
                
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_content += f"{shape.text.strip()}\n\n"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing PPTX: {str(e)}")
    
    def _process_json(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process JSON files"""
        try:
            import json
            
            text_content = content.decode('utf-8')
            data = json.loads(text_content)
            
            # Format JSON as readable text
            formatted_json = json.dumps(data, indent=2)
            
            # Add code block markers for better chunking
            text_content = f"```json\n{formatted_json}\n```"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing JSON: {str(e)}")
    
    def _process_yaml(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process YAML files"""
        try:
            import yaml
            
            text_content = content.decode('utf-8')
            data = yaml.safe_load(text_content)
            
            # Format YAML as readable text
            formatted_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
            
            # Add code block markers
            text_content = f"```yaml\n{formatted_yaml}\n```"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing YAML: {str(e)}")
    
    def _process_xml(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process XML files"""
        try:
            from bs4 import BeautifulSoup
            
            xml_content = content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(xml_content, 'xml')
            
            # Get pretty-printed XML
            text_content = soup.prettify()
            
            # Add code block markers
            text_content = f"```xml\n{text_content}\n```"
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing XML: {str(e)}")
    
    def _process_csv(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process CSV files"""
        try:
            import pandas as pd
            from io import BytesIO
            
            df = pd.read_csv(BytesIO(content))
            
            # Convert to markdown table
            text_content = f"## CSV Data\n\n"
            text_content += df.to_markdown(index=False)
            
            return chunk_document(text_content, filename, doc_id)
        except Exception as e:
            raise Exception(f"Error processing CSV: {str(e)}")
    
    def _process_doc(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process old Word documents (.doc) - requires conversion"""
        # .doc files are binary format, harder to parse
        # Option 1: Convert to .docx using LibreOffice (requires system dependency)
        # Option 2: Use textract or similar library
        raise Exception("Old .doc format not supported. Please convert to .docx first")
    
    def process(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
        """Process document based on file extension"""
        file_ext = os.path.splitext(filename)[1]
        processor = self.get_processor(file_ext)
        return processor(content, filename, doc_id)


# Global registry instance
document_processor_registry = DocumentProcessorRegistry()
```

### Step 3: Update Upload Endpoint

In `app/api/docs.py`, replace the file processing section:

```python
from app.services.document_processors import document_processor_registry

# In upload_document function, replace:
# Try to decode as text
try:
    text_content = content.decode('utf-8')
except:
    text_content = content.decode('utf-8', errors='ignore')

# Generate doc_id from content hash
doc_id = hashlib.md5(text_content.encode()).hexdigest()

# Chunk document using simple chunking logic
chunks = chunk_document(text_content, filename, doc_id)

# With:
# Process document based on file type
file_ext = os.path.splitext(filename)[1] if '.' in filename else ''

# Generate doc_id from content hash (before processing)
content_hash = hashlib.md5(content).hexdigest()
doc_id = content_hash

# Process document using registry
try:
    chunks = document_processor_registry.process(content, filename, doc_id)
except Exception as e:
    # Fallback to text processing
    try:
        text_content = content.decode('utf-8')
    except:
        text_content = content.decode('utf-8', errors='ignore')
    chunks = chunk_document(text_content, filename, doc_id)
```

### Step 4: Update Requirements

Add to `requirements.txt`:

```txt
python-docx>=1.0.0
openpyxl>=3.1.0
pandas>=2.0.0
python-pptx>=0.6.21
lxml>=4.9.0
ebooklib>=0.18
```

### Step 5: Rebuild Docker Image

```bash
docker compose build backend
docker compose up -d backend
```

---

## Supported File Types (After Implementation)

| Type | Extension | Status | Processor |
|------|-----------|--------|-----------|
| **Text Files** | `.txt`, `.md`, `.markdown` | ✅ Built-in | Text |
| **Code Files** | `.py`, `.js`, `.ts`, `.java`, etc. | ✅ Built-in | Code |
| **PDF** | `.pdf` | ⚠️ Available | PDFProcessor |
| **HTML** | `.html`, `.htm` | ⚠️ Available | HTMLProcessor |
| **Word** | `.docx` | 📝 To Add | DOCXProcessor |
| **Excel** | `.xlsx`, `.xls` | 📝 To Add | ExcelProcessor |
| **PowerPoint** | `.pptx` | 📝 To Add | PPTXProcessor |
| **JSON** | `.json` | 📝 To Add | JSONProcessor |
| **YAML** | `.yaml`, `.yml` | 📝 To Add | YAMLProcessor |
| **XML** | `.xml` | 📝 To Add | XMLProcessor |
| **CSV** | `.csv` | 📝 To Add | CSVProcessor |
| **EPUB** | `.epub` | 📝 To Add | EPUBProcessor |
| **RTF** | `.rtf` | 📝 To Add | RTFProcessor |

---

## Quick Implementation Steps

### Minimal Change Approach

1. **Create the processor registry** (`app/services/document_processors.py`)
2. **Update upload endpoint** to use registry
3. **Add required packages** to `requirements.txt`
4. **Rebuild and test**

### Example Integration (Minimal Change)

In `app/api/docs.py`, replace lines 42-64 with:

```python
import os
from app.services.document_processors import document_processor_registry

# ... existing code ...

# Detect file type and process
file_ext = os.path.splitext(filename)[1] if '.' in filename else ''

# Generate doc_id from content hash
doc_id = hashlib.md5(content).hexdigest()

# Check if document already exists
existing_doc = db.query(Document).filter(Document.id == doc_id).first()
if existing_doc:
    return UploadResponse(...)

# Process document using registry
try:
    chunks = document_processor_registry.process(content, filename, doc_id)
except Exception as e:
    # Fallback to text processing
    try:
        text_content = content.decode('utf-8')
    except:
        text_content = content.decode('utf-8', errors='ignore')
    chunks = chunk_document(text_content, filename, doc_id)
```

---

## Testing Different Document Types

After implementation, test with:

```bash
# PDF
curl -X POST http://localhost:8000/docs/upload -F "file=@document.pdf"

# Word document
curl -X POST http://localhost:8000/docs/upload -F "file=@document.docx"

# Excel
curl -X POST http://localhost:8000/docs/upload -F "file=@spreadsheet.xlsx"

# HTML
curl -X POST http://localhost:8000/docs/upload -F "file=@page.html"
```

---

## Advanced: Adding OCR for Images

To support scanned PDFs or images:

```python
def _process_image_pdf(self, content: bytes, filename: str, doc_id: str) -> List[ChunkMetadata]:
    """Process PDF with OCR for scanned documents"""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image
        
        # Convert PDF pages to images
        images = convert_from_bytes(content)
        text_content = ""
        
        for page_num, image in enumerate(images, 1):
            # OCR each page
            page_text = pytesseract.image_to_string(image)
            text_content += f"\n\n--- Page {page_num} (OCR) ---\n\n{page_text}"
        
        return chunk_document(text_content, filename, doc_id)
    except Exception as e:
        raise Exception(f"Error processing PDF with OCR: {str(e)}")
```

Add to requirements:
```txt
pytesseract>=0.3.10
pdf2image>=1.16.0
Pillow>=10.0.0
```

---

## Best Practices

1. **Always provide fallback**: If a processor fails, fallback to text processing
2. **Preserve structure**: Extract headings, sections, tables when possible
3. **Handle encoding**: Support multiple encodings (UTF-8, Latin-1, etc.)
4. **Memory management**: Process large files in chunks
5. **Error handling**: Provide clear error messages for unsupported formats

---

## Current Status

**To enable existing processors (PDF, HTML):**

Just update `app/api/docs.py` to use the file extension to route to the right processor. The `PDFProcessor` and `HTMLProcessor` classes already exist in `app/services/processing.py`.

---

## Summary

The system is ready to support more document types. To add support:

1. ✅ Create processor classes for each format
2. ✅ Register them in a processor registry
3. ✅ Update upload endpoint to detect file type and route appropriately
4. ✅ Add required Python packages
5. ✅ Rebuild Docker image

The chunking logic (`chunk_document`) works with any text content, so once you extract text from documents, the rest works automatically.

