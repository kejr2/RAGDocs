# RAGDocs Architecture: Document Flow Explained

This document explains how documents are received, processed, stored, and retrieved in the RAGDocs system.

---

## Table of Contents

1. [Overview](#overview)
2. [Document Upload Flow](#document-upload-flow)
3. [Storage Architecture](#storage-architecture)
4. [Document ID (doc_id)](#document-id-doc_id)
5. [Chunking Process](#chunking-process)
6. [Embedding & Vector Storage](#embedding--vector-storage)
7. [Retrieval Flow](#retrieval-flow)
8. [Query Processing](#query-processing)
9. [Data Flow Diagrams](#data-flow-diagrams)

---

## Overview

The RAGDocs system uses a **dual-database architecture**:

- **PostgreSQL**: Stores document and chunk metadata (structured data)
- **Qdrant**: Stores vector embeddings for semantic search (vector database)

This separation allows for:
- Fast metadata queries via PostgreSQL
- Efficient semantic search via Qdrant
- Scalable vector operations
- Rich metadata without bloating vector storage

---

## Document Upload Flow

### Step-by-Step Process

```
1. Client uploads file
   ↓
2. FastAPI receives UploadFile
   ↓
3. File content read as bytes
   ↓
4. Document ID (doc_id) generated from content hash
   ↓
5. Check if document already exists (duplicate detection)
   ↓
6. File type detection (PDF, HTML, or text)
   ↓
7. Document processing (extract text from PDF/HTML)
   ↓
8. Chunking (split into text/code chunks)
   ↓
9. Generate embeddings (text & code separately)
   ↓
10. Store in Qdrant (vectors + metadata payload)
    ↓
11. Store in PostgreSQL (document & chunk metadata)
    ↓
12. Return response with doc_id
```

### Code Location

**Endpoint**: `app/api/docs.py` → `upload_document()`

---

## Storage Architecture

### What is Stored Where?

#### PostgreSQL (`postgres` container)

**Table: `documents`**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | String (PK) | Document ID (MD5 hash) | `"abc123..."` |
| `filename` | String | Original filename | `"fastapi_docs.pdf"` |
| `content_hash` | String | Same as `id` (for deduplication) | `"abc123..."` |
| `total_chunks` | Integer | Total number of chunks | `42` |
| `text_chunks` | Integer | Number of text chunks | `35` |
| `code_chunks` | Integer | Number of code chunks | `7` |
| `created_at` | DateTime | Upload timestamp | `2025-01-01 10:00:00` |
| `updated_at` | DateTime | Last update timestamp | `2025-01-01 10:00:00` |

**Table: `chunks`**
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | String (PK) | Chunk ID (UUID) | `"chunk-uuid-123"` |
| `doc_id` | String (FK, Indexed) | Reference to document | `"abc123..."` |
| `source_file` | String | Original filename | `"fastapi_docs.pdf"` |
| `content` | Text | Full chunk content | `"FastAPI is a modern..."` |
| `start` | Integer | Line number start | `5` |
| `end` | Integer | Line number end | `25` |
| `chunk_type` | String | `"text"` or `"code"` | `"text"` |
| `heading` | String | Section heading | `"## What is FastAPI?"` |
| `language` | String | Code language (if code chunk) | `"python"` |
| `created_at` | DateTime | Creation timestamp | `2025-01-01 10:00:00` |

**Purpose of PostgreSQL:**
- ✅ Fast metadata queries ("Get all chunks for doc_id X")
- ✅ Structured relationships (document → chunks)
- ✅ Deduplication (check if document already exists)
- ✅ Full-text content storage (for reference)
- ✅ Metadata filtering and sorting

---

#### Qdrant (`qdrant` container)

**Collection: `text_chunks`**
- **Vector Dimension**: 384 (from `all-MiniLM-L6-v2` model)
- **Distance Metric**: Cosine
- **Each Point Contains**:
  - `id`: Chunk ID (UUID) - used as point ID
  - `vector`: Embedding vector (384-dimensional)
  - `payload`: Metadata object:
    ```json
    {
      "chunk_id": "chunk-uuid-123",
      "doc_id": "abc123...",
      "source_file": "fastapi_docs.pdf",
      "start": 5,
      "end": 25,
      "type": "text",
      "heading": "## What is FastAPI?",
      "content": "FastAPI is a modern web framework..."
    }
    ```

**Collection: `code_chunks`**
- **Vector Dimension**: 768 (from `jinaai/jina-embeddings-v2-base-code` model)
- **Distance Metric**: Cosine
- **Each Point Contains**:
  - `id`: Chunk ID (UUID)
  - `vector`: Code embedding vector (768-dimensional)
  - `payload`: Metadata object (same structure, plus `language` field):
    ```json
    {
      "chunk_id": "chunk-uuid-456",
      "doc_id": "abc123...",
      "source_file": "fastapi_docs.pdf",
      "start": 30,
      "end": 45,
      "type": "code",
      "heading": "## Quick Example",
      "language": "python",
      "content": "from fastapi import FastAPI\n..."
    }
    ```

**Purpose of Qdrant:**
- ✅ Fast semantic similarity search
- ✅ Vector-based retrieval (nearest neighbors)
- ✅ Efficient similarity calculations
- ✅ Filtering by metadata (e.g., `doc_id`)
- ✅ Hybrid search across text and code

---

### Why Two Databases?

| Feature | PostgreSQL | Qdrant |
|---------|-----------|---------|
| **Purpose** | Metadata & relationships | Vector similarity search |
| **Query Type** | SQL queries, joins | Vector similarity, nearest neighbors |
| **Speed** | Fast for structured queries | Fast for semantic search |
| **Content Storage** | Full chunk content | Full chunk content (in payload) |
| **Indexing** | B-tree indexes | Vector indexes (HNSW) |

**Best of Both Worlds:**
- PostgreSQL: Reliable, ACID-compliant, structured queries
- Qdrant: Specialized vector operations, optimized for embeddings

---

## Document ID (doc_id)

### What is `doc_id`?

The `doc_id` is a **unique identifier** for each document, generated from the document's content.

### How is it Generated?

```python
# From app/api/docs.py, line 48
doc_id = hashlib.md5(content).hexdigest()
```

**Algorithm**: MD5 hash of the raw file content (bytes)

**Example**:
- File: `fastapi_docs.pdf` (1MB)
- MD5 hash: `a1b2c3d4e5f6...` (32-character hex string)
- `doc_id`: `"a1b2c3d4e5f6..."`

### Where is `doc_id` Stored?

1. **PostgreSQL `documents` table**:
   - Column: `id` (Primary Key)
   - Column: `content_hash` (same value)

2. **PostgreSQL `chunks` table**:
   - Column: `doc_id` (Foreign Key, indexed)

3. **Qdrant collections**:
   - In **every point's payload**: `payload["doc_id"]`
   - Used for filtering queries (e.g., "only search chunks from this document")

### Why MD5 Hash?

- ✅ **Deterministic**: Same content → same `doc_id`
- ✅ **Deduplication**: Uploading the same file twice → detects duplicate
- ✅ **Unique**: Different content → different `doc_id`
- ✅ **Fast**: MD5 is fast to compute
- ✅ **Fixed Length**: Always 32 characters (hex)

### Usage

```python
# Check if document exists (deduplication)
existing_doc = db.query(Document).filter(Document.id == doc_id).first()

# Filter Qdrant search to specific document
query_filter = Filter(
    must=[
        FieldCondition(
            key="doc_id",
            match=MatchValue(value=doc_id)
        )
    ]
)

# Get all chunks for a document
chunks = db.query(Chunk).filter(Chunk.doc_id == doc_id).all()
```

---

## Chunking Process

### What is Chunking?

Chunking splits a document into smaller pieces (chunks) that are:
- Small enough to fit in embeddings
- Large enough to preserve context
- Separated by type (text vs code)

### Chunking Logic

**Location**: `app/services/chunking.py` → `chunk_document()`

**Process**:
1. Split document into lines
2. Detect code blocks (```markdown code blocks)
3. Detect headings (`# Heading`)
4. Create chunks:
   - **Code chunks**: Extracted from code blocks
   - **Text chunks**: Created every ~600 characters or at headings

**Chunk Metadata Created**:
```python
@dataclass
class ChunkMetadata:
    chunk_id: str          # UUID
    doc_id: str           # Document ID
    source_file: str      # Original filename
    content: str          # Chunk text
    start: int            # Line number start
    end: int              # Line number end
    type: str             # "text" or "code"
    heading: str          # Section heading (if any)
    language: str         # Code language (if code chunk)
```

### Example

**Input Document**:
```markdown
## What is FastAPI?

FastAPI is a modern web framework...

## Quick Example

```python
from fastapi import FastAPI
app = FastAPI()
```
```

**Output Chunks**:
1. Text chunk: `"## What is FastAPI?\n\nFastAPI is a modern web framework..."`
2. Code chunk: `"from fastapi import FastAPI\napp = FastAPI()"` (language: `"python"`)

### Chunk Types

| Type | Detection | Purpose |
|------|-----------|---------|
| **Text** | Regular paragraphs, headings | General content, explanations |
| **Code** | Markdown code blocks (` ``` `) | Code examples, snippets |

---

## Embedding & Vector Storage

### Embedding Models

**Text Embeddings**: `all-MiniLM-L6-v2`
- Dimension: **384**
- Used for: Text chunks
- Model type: Sentence Transformer

**Code Embeddings**: `jinaai/jina-embeddings-v2-base-code`
- Dimension: **768**
- Used for: Code chunks
- Model type: Code-optimized transformer

### Embedding Process

**Location**: `app/services/embeddings.py` → `EmbeddingService`

**For Text Chunks**:
```python
text_contents = [chunk.content for chunk in text_chunks]
text_embeddings = embedding_service.encode_text(text_contents)
# Returns: List[List[float]] - 384-dimensional vectors
```

**For Code Chunks**:
```python
code_contents = [chunk.content for chunk in code_chunks]
code_embeddings = embedding_service.encode_code(code_contents)
# Returns: List[List[float]] - 768-dimensional vectors
```

### Storage in Qdrant

**Location**: `app/api/docs.py` → lines 104-159

**Process**:
1. Generate embeddings for all chunks
2. Create `PointStruct` objects:
   ```python
   PointStruct(
       id=chunk.chunk_id,           # UUID (used as point ID)
       vector=embedding,            # Vector (384 or 768 dims)
       payload={                    # Metadata
           "chunk_id": chunk.chunk_id,
           "doc_id": chunk.doc_id,
           "source_file": chunk.source_file,
           "start": chunk.start,
           "end": chunk.end,
           "type": chunk.type,
           "heading": chunk.heading or "",
           "content": chunk.content,  # Full content stored in payload
           "language": chunk.language or ""  # For code chunks
       }
   )
   ```
3. Upsert to Qdrant:
   - Text chunks → `text_chunks` collection
   - Code chunks → `code_chunks` collection

**Why Store Content in Payload?**
- ✅ No need to query PostgreSQL for chunk content during retrieval
- ✅ Faster: Everything needed for response is in Qdrant
- ✅ Redundant storage ensures availability

---

## Retrieval Flow

### Overview

When a user queries the system:
1. Query is embedded (using appropriate model)
2. Vector similarity search in Qdrant
3. Results are reranked and filtered
4. Context is built from top results
5. LLM (Gemini) generates answer
6. Response returned to user

### Step-by-Step Retrieval

```
1. User query received
   ↓
2. Detect query type (text/code/hybrid)
   ↓
3. Embed query:
   - Text embedding (384-dim) for text_chunks
   - Code embedding (768-dim) for code_chunks
   ↓
4. Search Qdrant:
   - Search text_chunks collection (if text/hybrid query)
   - Search code_chunks collection (if code/hybrid query)
   ↓
5. Apply filters (optional doc_id filter)
   ↓
6. Get top-K results (by similarity score)
   ↓
7. Rerank results (boost matching headings, definitions)
   ↓
8. Extract content from payload
   ↓
9. Build context string
   ↓
10. Send to Gemini LLM
    ↓
11. Generate answer
    ↓
12. Return response
```

### Code Location

**Endpoint**: `app/api/chat.py` → `query_chat()`

---

## Query Processing

### Query Request

```json
{
  "query": "What is FastAPI?",
  "doc_id": "abc123...",  // Optional: filter to specific document
  "top_k": 5              // Number of results to retrieve
}
```

### Hybrid Search Strategy

The system uses **hybrid search** for better results:

1. **Text Collection Search** (always):
   - Embed query with text model
   - Search `text_chunks` collection
   - Get `top_k * 2` results (wider search)

2. **Code Collection Search** (when relevant):
   - If query contains code keywords
   - If query is definition-type ("what is", "explain")
   - Embed query with code model
   - Search `code_chunks` collection
   - Get `top_k` results

3. **Combine & Rerank**:
   - Merge results from both collections
   - Boost results with matching headings
   - Sort by relevance score
   - Take top `top_k` results

### Filtering by `doc_id`

If `doc_id` is provided:
```python
query_filter = Filter(
    must=[
        FieldCondition(
            key="doc_id",
            match=MatchValue(value=doc_id)
        )
    ]
)
```

**Without `doc_id`**: Searches ALL uploaded documents

**With `doc_id`**: Searches only chunks from that document

### Reranking Logic

**Location**: `app/api/chat.py` → `boost_score()`

**Boosting Rules**:
1. **Definition Questions**: If query contains "what is", "what are", "explain":
   - Strong boost if heading matches topic (e.g., `"## What is FastAPI?"`)
   - Medium boost if heading contains topic

2. **Heading Matches**: Boost chunks with relevant headings

3. **Type Matching**: Prioritize code chunks for code queries

### Context Building

**Location**: `app/api/chat.py` → lines 162-169

**Process**:
1. Extract content and heading from each result
2. Format: `"{heading}\n{content}"` (if heading exists)
3. Join chunks with `"\n\n---\n\n"`
4. Create context string for LLM

**Example Context**:
```
## What is FastAPI?

FastAPI is a modern web framework for building APIs...

---

## Quick Example

```python
from fastapi import FastAPI
app = FastAPI()
```
```

### Answer Generation

**Location**: `app/services/gemini.py` → `generate_answer()`

**Process**:
1. Build prompt with context and query
2. Send to Gemini API
3. Generate answer
4. Return formatted response

**Fallback**: If Gemini fails, format basic answer from retrieved sources

### Query Response

```json
{
  "answer": "FastAPI is a modern web framework...",
  "sources": [
    {
      "content": "FastAPI is a modern web framework...",
      "metadata": {
        "chunk_id": "chunk-uuid-123",
        "doc_id": "abc123...",
        "source_file": "fastapi_docs.pdf",
        "type": "text",
        "heading": "## What is FastAPI?",
        "relevance_score": 0.95
      }
    }
  ],
  "context_used": [
    "## What is FastAPI?\n\nFastAPI is a modern web framework...",
    "..."
  ]
}
```

---

## Data Flow Diagrams

### Upload Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /docs/upload
       │ (file)
       ↓
┌──────────────────┐
│  FastAPI Endpoint │
│  (app/api/docs.py)│
└──────┬───────────┘
       │
       ├─→ Read file content (bytes)
       ├─→ Generate doc_id (MD5 hash)
       ├─→ Check duplicate (PostgreSQL)
       ├─→ Process file (PDF/HTML/text)
       ├─→ Chunk document
       │
       ├─→ Generate embeddings
       │   ├─→ Text embeddings (384-dim)
       │   └─→ Code embeddings (768-dim)
       │
       ├─→ Store in Qdrant
       │   ├─→ text_chunks collection
       │   └─→ code_chunks collection
       │
       ├─→ Store in PostgreSQL
       │   ├─→ documents table
       │   └─→ chunks table
       │
       └─→ Return doc_id
```

### Retrieval Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /chat/query
       │ {"query": "...", "doc_id": "..."}
       ↓
┌──────────────────┐
│  FastAPI Endpoint │
│  (app/api/chat.py)│
└──────┬───────────┘
       │
       ├─→ Detect query type
       ├─→ Embed query
       │   ├─→ Text embedding (384-dim)
       │   └─→ Code embedding (768-dim)
       │
       ├─→ Search Qdrant
       │   ├─→ text_chunks collection
       │   └─→ code_chunks collection
       │   └─→ Apply filters (doc_id)
       │
       ├─→ Rerank results
       ├─→ Build context
       ├─→ Send to Gemini LLM
       └─→ Return answer + sources
```

### Storage Architecture

```
┌─────────────────────────────────────────────┐
│           Uploaded Document                 │
│     (e.g., fastapi_docs.pdf)               │
└──────────────────┬──────────────────────────┘
                   │
                   ├─────────────────────────┐
                   │                         │
                   ↓                         ↓
        ┌──────────────────┐      ┌──────────────────┐
        │   PostgreSQL     │      │     Qdrant       │
        │  (Metadata DB)    │      │  (Vector DB)     │
        └──────────────────┘      └──────────────────┘
                   │                         │
        ┌──────────┴──────────┐    ┌──────────┴──────────┐
        │  documents table    │    │  text_chunks        │
        │  - id (doc_id)      │    │  - vector (384-dim) │
        │  - filename         │    │  - payload         │
        │  - total_chunks     │    │    - doc_id         │
        │  - text_chunks      │    │    - content        │
        │  - code_chunks      │    │    - heading        │
        │                     │    │                     │
        │  chunks table       │    │  code_chunks        │
        │  - id (chunk_id)    │    │  - vector (768-dim) │
        │  - doc_id (FK)      │    │  - payload         │
        │  - content          │    │    - doc_id         │
        │  - chunk_type       │    │    - content        │
        │  - heading         │    │    - language       │
        │  - language        │    │                     │
        └────────────────────┘    └─────────────────────┘
```

---

## Key Takeaways

1. **Document ID (`doc_id`)**:
   - Generated from MD5 hash of file content
   - Used for deduplication and filtering
   - Stored in PostgreSQL (`documents.id`) and Qdrant payloads

2. **Storage Strategy**:
   - **PostgreSQL**: Metadata, relationships, full content
   - **Qdrant**: Vector embeddings + metadata payload (for fast retrieval)

3. **Chunking**:
   - Documents split into text and code chunks
   - Each chunk has metadata (heading, language, position)

4. **Embeddings**:
   - Text chunks: 384-dimensional vectors
   - Code chunks: 768-dimensional vectors
   - Stored in separate Qdrant collections

5. **Retrieval**:
   - Hybrid search (text + code collections)
   - Reranking with heading/topic matching
   - Context built from top results
   - Answer generated by Gemini LLM

6. **Query Flexibility**:
   - With `doc_id`: Search specific document
   - Without `doc_id`: Search all documents

---

## File References

- **Upload Endpoint**: `app/api/docs.py`
- **Query Endpoint**: `app/api/chat.py`
- **Chunking**: `app/services/chunking.py`
- **Embeddings**: `app/services/embeddings.py`
- **Retrieval**: `app/services/retrieval.py`
- **Database Models**: `app/models/document.py`
- **Qdrant Client**: `app/core/qdrant_client.py`
- **Gemini Service**: `app/services/gemini.py`

---

## Summary

The RAGDocs system processes documents through a pipeline:
1. **Upload** → Extract text, chunk, embed
2. **Store** → PostgreSQL (metadata) + Qdrant (vectors)
3. **Retrieve** → Vector similarity search, rerank, context building
4. **Generate** → LLM-powered answers from retrieved context

The `doc_id` ties everything together, enabling efficient filtering and deduplication across both databases.

