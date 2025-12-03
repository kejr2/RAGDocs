# RAGDocs Backend API Documentation

Complete API reference for frontend development.

**Base URL**: `http://localhost:8000`  
**API Version**: `1.0.0`

---

## Table of Contents

1. [Overview](#overview)
2. [Health Check](#health-check)
3. [Document Upload](#document-upload)
4. [Chat/Query](#chatquery)
5. [Get Document Chunks](#get-document-chunks)
6. [Delete Document](#delete-document)
7. [Request/Response Formats](#requestresponse-formats)
8. [Error Handling](#error-handling)
9. [Example Requests](#example-requests)
10. [CORS Configuration](#cors-configuration)

---

## Overview

The RAGDocs API is a RESTful API built with FastAPI for document upload, vector search, and AI-powered question answering.

### Base Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs/upload` | POST | Upload document |
| `/chat/query` | POST | Query documents |
| `/docs/chunks/{doc_id}` | GET | Get document chunks |
| `/docs/documents/{doc_id}` | DELETE | Delete document |
| `/docs` | GET | FastAPI Swagger UI (auto-generated) |
| `/redoc` | GET | FastAPI ReDoc (auto-generated) |

### Response Format

All responses are JSON. Success responses include data, error responses include `detail`.

---

## Health Check

Check if the API is running and Gemini AI is enabled.

### Endpoint

```
GET /health
```

### Request

No parameters required.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T10:00:00.000000",
  "gemini_enabled": true
}
```

### Example

```bash
curl http://localhost:8000/health
```

### Response Codes

| Code | Description |
|------|-------------|
| 200 | API is healthy |
| 500 | Internal server error |

---

## Document Upload

Upload a document (PDF, HTML, text, code files) for processing and indexing.

### Endpoint

```
POST /docs/upload
```

### Request

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Document file to upload |
| `source_type` | String | No | Optional source type identifier |

### Supported File Types

- **PDF**: `.pdf`
- **HTML**: `.html`, `.htm`
- **Text**: `.txt`, `.md`, `.markdown`
- **Code**: `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.c`, `.go`, `.rs`, `.rb`, `.php`

### Response

```json
{
  "doc_id": "a1b2c3d4e5f6...",
  "filename": "document.pdf",
  "total_chunks": 12,
  "text_chunks": 10,
  "code_chunks": 2,
  "status": "success"
}
```

**Status Values**:
- `"success"`: Document uploaded and processed successfully
- `"already_exists"`: Document already exists (same content hash)

### Example

```bash
# Using curl
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@document.pdf"

# Using curl with source_type
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@document.pdf" \
  -F "source_type=api_docs"
```

### JavaScript/TypeScript Example

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('source_type', 'api_docs'); // Optional

const response = await fetch('http://localhost:8000/docs/upload', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log('Document ID:', data.doc_id);
```

### Response Codes

| Code | Description |
|------|-------------|
| 201 | Document uploaded successfully |
| 400 | Invalid file or missing file parameter |
| 500 | Error processing document |

---

## Chat/Query

Query the RAG system with a question. The system uses LLM-enhanced queries and hybrid retrieval.

### Endpoint

```
POST /chat/query
```

### Request

**Content-Type**: `application/json`

```json
{
  "query": "What is FastAPI?",
  "doc_id": "a1b2c3d4e5f6...",  // Optional: filter to specific document
  "top_k": 5                     // Optional: number of results (default: 10)
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | String | Yes | Question to ask |
| `doc_id` | String | No | Filter to specific document (omit to search all) |
| `top_k` | Integer | No | Number of results to retrieve (default: 10) |

### Response

```json
{
  "answer": "FastAPI is a modern web framework for building APIs...",
  "sources": [
    {
      "content": "FastAPI is a modern web framework...",
      "metadata": {
        "chunk_id": "chunk-uuid-123",
        "doc_id": "a1b2c3d4e5f6...",
        "source_file": "document.pdf",
        "start": 5,
        "end": 25,
        "type": "text",
        "heading": "## What is FastAPI?",
        "language": ""
      },
      "relevance_score": 0.95
    }
  ],
  "context_used": [
    "## What is FastAPI?\n\nFastAPI is a modern web framework...",
    "..."
  ]
}
```

### Response Fields

- **`answer`**: AI-generated answer (from Gemini LLM or basic formatting)
- **`sources`**: Array of retrieved chunks with metadata and relevance scores
- **`context_used`**: Array of context chunks (with headings) sent to LLM

### Example

```bash
# Query all documents
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "top_k": 5
  }'

# Query specific document
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "doc_id": "a1b2c3d4e5f6...",
    "top_k": 5
  }'
```

### JavaScript/TypeScript Example

```javascript
const response = await fetch('http://localhost:8000/chat/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'What is FastAPI?',
    doc_id: 'a1b2c3d4e5f6...', // Optional
    top_k: 5
  })
});

const data = await response.json();
console.log('Answer:', data.answer);
console.log('Sources:', data.sources);
```

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Query processed successfully |
| 400 | Invalid request (missing query) |
| 500 | Error processing query |

---

## Get Document Chunks

Get all chunks for a specific document.

### Endpoint

```
GET /docs/chunks/{doc_id}
```

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | String | Yes | Document ID (from upload response) |

### Response

```json
{
  "doc_id": "a1b2c3d4e5f6...",
  "chunks": [
    {
      "chunk_id": "chunk-uuid-123",
      "doc_id": "a1b2c3d4e5f6...",
      "source_file": "document.pdf",
      "content": "FastAPI is a modern web framework...",
      "start": 5,
      "end": 25,
      "type": "text",
      "heading": "## What is FastAPI?",
      "language": ""
    }
  ]
}
```

### Example

```bash
curl http://localhost:8000/docs/chunks/a1b2c3d4e5f6...
```

### JavaScript/TypeScript Example

```javascript
const response = await fetch(
  `http://localhost:8000/docs/chunks/${docId}`
);
const data = await response.json();
console.log('Chunks:', data.chunks);
```

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Chunks retrieved successfully |
| 404 | Document not found |
| 500 | Error retrieving chunks |

---

## Delete Document

Delete a document and all its associated chunks from both PostgreSQL and Qdrant.

### Endpoint

```
DELETE /docs/documents/{doc_id}
```

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | String | Yes | Document ID to delete |

### Response

```json
{
  "message": "Document deleted successfully",
  "doc_id": "a1b2c3d4e5f6...",
  "chunks_deleted": 12
}
```

### Example

```bash
curl -X DELETE http://localhost:8000/docs/documents/a1b2c3d4e5f6...
```

### JavaScript/TypeScript Example

```javascript
const response = await fetch(
  `http://localhost:8000/docs/documents/${docId}`,
  {
    method: 'DELETE'
  }
);
const data = await response.json();
console.log('Deleted:', data.message);
```

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Document deleted successfully |
| 404 | Document not found |
| 500 | Error deleting document |

---

## Request/Response Formats

### Common Request Headers

```
Content-Type: application/json  # For JSON requests
Content-Type: multipart/form-data  # For file uploads
```

### Common Response Headers

```
Content-Type: application/json
```

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Example Error Response

```json
{
  "detail": "Error processing document: Invalid file format"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created (upload) |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Error Response

All errors return JSON:

```json
{
  "detail": "Error message"
}
```

### Common Errors

**1. Missing File (Upload)**
```json
{
  "detail": "Missing file parameter"
}
```
**Solution**: Ensure `file` is included in form data.

**2. Invalid Document ID**
```json
{
  "detail": "Document not found"
}
```
**Solution**: Use a valid `doc_id` from upload response.

**3. Server Error**
```json
{
  "detail": "Error querying document: ..."
}
```
**Solution**: Check server logs for details.

---

## Example Requests

### Complete Workflow Example

#### 1. Check Health

```bash
curl http://localhost:8000/health
```

#### 2. Upload Document

```bash
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "doc_id": "34728f7c187d1f20188566250de673f2",
  "filename": "document.pdf",
  "total_chunks": 12,
  "text_chunks": 10,
  "code_chunks": 2,
  "status": "success"
}
```

#### 3. Query Document

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this document about?",
    "doc_id": "34728f7c187d1f20188566250de673f2",
    "top_k": 5
  }'
```

#### 4. Get Chunks

```bash
curl http://localhost:8000/docs/chunks/34728f7c187d1f20188566250de673f2
```

#### 5. Delete Document

```bash
curl -X DELETE http://localhost:8000/docs/documents/34728f7c187d1f20188566250de673f2
```

---

## CORS Configuration

The API is configured with CORS to allow frontend requests:

```python
allow_origins=["*"]  # Configure appropriately for production
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

**For Production**: Replace `["*"]` with your frontend domain:
```python
allow_origins=["https://your-frontend-domain.com"]
```

---

## Frontend Integration Guide

### TypeScript Interfaces

```typescript
// Health Response
interface HealthResponse {
  status: string;
  timestamp: string;
  gemini_enabled: boolean;
}

// Upload Response
interface UploadResponse {
  doc_id: string;
  filename: string;
  total_chunks: number;
  text_chunks: number;
  code_chunks: number;
  status: "success" | "already_exists";
}

// Query Request
interface QueryRequest {
  query: string;
  doc_id?: string;
  top_k?: number;
}

// Query Response
interface QueryResponse {
  answer: string;
  sources: Source[];
  context_used: string[];
}

// Source
interface Source {
  content: string;
  metadata: {
    chunk_id: string;
    doc_id: string;
    source_file: string;
    start: number;
    end: number;
    type: "text" | "code";
    heading: string;
    language: string;
  };
  relevance_score: number;
}

// Chunks Response
interface ChunksResponse {
  doc_id: string;
  chunks: Chunk[];
}

// Chunk
interface Chunk {
  chunk_id: string;
  doc_id: string;
  source_file: string;
  content: string;
  start: number;
  end: number;
  type: "text" | "code";
  heading: string;
  language: string;
}

// Delete Response
interface DeleteResponse {
  message: string;
  doc_id: string;
  chunks_deleted: number;
}
```

### React Example

```typescript
import React, { useState } from 'react';

const API_BASE = 'http://localhost:8000';

export function RAGDocsClient() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);

  const handleQuery = async () => {
    const response = await fetch(`${API_BASE}/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        top_k: 5
      })
    });
    
    const data = await response.json();
    setAnswer(data.answer);
    setSources(data.sources);
  };

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/docs/upload`, {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    console.log('Uploaded:', data.doc_id);
    return data;
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={handleQuery}>Ask</button>
      <div>{answer}</div>
      <div>
        <h3>Sources:</h3>
        {sources.map((source, i) => (
          <div key={i}>
            <p>{source.content}</p>
            <small>Relevance: {source.relevance_score}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### JavaScript Fetch Examples

```javascript
// Health Check
async function checkHealth() {
  const response = await fetch('http://localhost:8000/health');
  const data = await response.json();
  return data;
}

// Upload Document
async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/docs/upload', {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

// Query Documents
async function queryDocuments(query, docId = null, topK = 5) {
  const response = await fetch('http://localhost:8000/chat/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      doc_id: docId,
      top_k: topK
    })
  });

  return await response.json();
}

// Get Document Chunks
async function getChunks(docId) {
  const response = await fetch(
    `http://localhost:8000/docs/chunks/${docId}`
  );
  return await response.json();
}

// Delete Document
async function deleteDocument(docId) {
  const response = await fetch(
    `http://localhost:8000/docs/documents/${docId}`,
    {
      method: 'DELETE'
    }
  );
  return await response.json();
}
```

---

## Swagger UI

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide:
- Interactive API testing
- Request/response schemas
- Try-it-out functionality
- API documentation

---

## Rate Limiting

Currently, there is no rate limiting. For production, consider implementing:
- Rate limiting per IP
- Rate limiting per API key
- Request throttling

---

## Authentication

Currently, there is no authentication. For production, consider:
- API key authentication
- JWT tokens
- OAuth2
- Session-based authentication

---

## Testing

### Using curl

See [Example Requests](#example-requests) section above.

### Using Postman/Insomnia

1. Import the endpoints
2. Set base URL: `http://localhost:8000`
3. For uploads, use form-data with `file` field
4. For queries, use JSON body

---

## Summary

**Available Endpoints:**

1. ✅ `GET /health` - Health check
2. ✅ `POST /docs/upload` - Upload document
3. ✅ `POST /chat/query` - Query documents
4. ✅ `GET /docs/chunks/{doc_id}` - Get document chunks
5. ✅ `DELETE /docs/documents/{doc_id}` - Delete document
6. ✅ `GET /docs` - Swagger UI (auto-generated)
7. ✅ `GET /redoc` - ReDoc (auto-generated)

**Key Features:**

- ✅ Document upload (PDF, HTML, text, code)
- ✅ LLM-enhanced query processing
- ✅ Hybrid retrieval (text + code)
- ✅ AI-powered answer generation
- ✅ Source attribution
- ✅ Document management

**Ready for Frontend Integration!** 🚀




