# Frontend Setup Guide

Quick start guide for building a frontend for RAGDocs.

---

## Prerequisites

- Node.js 16+ (for React/Vue/Angular)
- Or HTML/CSS/JavaScript knowledge (for vanilla JS)
- API running at `http://localhost:8000`

---

## Quick Start

### Option 1: React with TypeScript

```bash
npx create-react-app ragdocs-frontend --template typescript
cd ragdocs-frontend
npm install axios  # For API calls
npm start
```

### Option 2: Vue.js

```bash
npm create vue@latest ragdocs-frontend
cd ragdocs-frontend
npm install axios
npm run dev
```

### Option 3: Vanilla JavaScript

Just create an HTML file and use `fetch` API.

---

## API Client Library

### Create `src/api/ragdocs.ts`

```typescript
const API_BASE = 'http://localhost:8000';

export interface HealthResponse {
  status: string;
  timestamp: string;
  gemini_enabled: boolean;
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  total_chunks: number;
  text_chunks: number;
  code_chunks: number;
  status: 'success' | 'already_exists';
}

export interface QueryRequest {
  query: string;
  doc_id?: string;
  top_k?: number;
}

export interface Source {
  content: string;
  metadata: {
    chunk_id: string;
    doc_id: string;
    source_file: string;
    start: number;
    end: number;
    type: 'text' | 'code';
    heading: string;
    language: string;
  };
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  context_used: string[];
}

export interface Chunk {
  chunk_id: string;
  doc_id: string;
  source_file: string;
  content: string;
  start: number;
  end: number;
  type: 'text' | 'code';
  heading: string;
  language: string;
}

export interface ChunksResponse {
  doc_id: string;
  chunks: Chunk[];
}

export interface DeleteResponse {
  message: string;
  doc_id: string;
  chunks_deleted: number;
}

class RAGDocsClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }

  async uploadDocument(
    file: File,
    sourceType?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceType) {
      formData.append('source_type', sourceType);
    }

    const response = await fetch(`${this.baseUrl}/docs/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async queryDocuments(
    query: string,
    docId?: string,
    topK: number = 5
  ): Promise<QueryResponse> {
    const response = await fetch(`${this.baseUrl}/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        doc_id: docId,
        top_k: topK,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Query failed');
    }

    return response.json();
  }

  async getChunks(docId: string): Promise<ChunksResponse> {
    const response = await fetch(`${this.baseUrl}/docs/chunks/${docId}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get chunks');
    }
    return response.json();
  }

  async deleteDocument(docId: string): Promise<DeleteResponse> {
    const response = await fetch(`${this.baseUrl}/docs/documents/${docId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Delete failed');
    }

    return response.json();
  }
}

export const ragdocsClient = new RAGDocsClient();
export default RAGDocsClient;
```

---

## Example React Components

### Document Upload Component

```typescript
import React, { useState } from 'react';
import { ragdocsClient, UploadResponse } from './api/ragdocs';

export function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    try {
      const response = await ragdocsClient.uploadDocument(file);
      setResult(response);
      alert(`Document uploaded! ID: ${response.doc_id}`);
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input type="file" onChange={handleFileChange} accept=".pdf,.html,.txt,.md" />
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Upload'}
      </button>
      {result && (
        <div>
          <p>Document ID: {result.doc_id}</p>
          <p>Chunks: {result.total_chunks} ({result.text_chunks} text, {result.code_chunks} code)</p>
        </div>
      )}
    </div>
  );
}
```

### Query Component

```typescript
import React, { useState } from 'react';
import { ragdocsClient, QueryResponse, Source } from './api/ragdocs';

export function QueryComponent() {
  const [query, setQuery] = useState('');
  const [docId, setDocId] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  const handleQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const result = await ragdocsClient.queryDocuments(
        query,
        docId || undefined,
        5
      );
      setResponse(result);
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a question..."
        style={{ width: '100%', padding: '10px' }}
      />
      <input
        type="text"
        value={docId}
        onChange={(e) => setDocId(e.target.value)}
        placeholder="Document ID (optional)"
        style={{ width: '100%', padding: '10px', marginTop: '10px' }}
      />
      <button onClick={handleQuery} disabled={loading}>
        {loading ? 'Querying...' : 'Ask'}
      </button>

      {response && (
        <div style={{ marginTop: '20px' }}>
          <h3>Answer:</h3>
          <div style={{ padding: '15px', background: '#f5f5f5', borderRadius: '5px' }}>
            {response.answer}
          </div>

          <h3>Sources ({response.sources.length}):</h3>
          {response.sources.map((source, i) => (
            <div key={i} style={{ marginTop: '10px', padding: '10px', border: '1px solid #ddd' }}>
              <p><strong>{source.metadata.heading || 'No heading'}</strong></p>
              <p>{source.content.substring(0, 200)}...</p>
              <small>Relevance: {(source.relevance_score * 100).toFixed(1)}%</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Complete Example App

See the `API_DOCUMENTATION.md` for complete API reference and examples.

---

## Key Features to Implement

1. **Document Upload**
   - File picker
   - Progress indicator
   - Upload status
   - Document ID display

2. **Query Interface**
   - Search bar
   - Document filter (optional)
   - Answer display
   - Source citations
   - Loading states

3. **Document Management**
   - List uploaded documents
   - View chunks
   - Delete documents

4. **Error Handling**
   - Network errors
   - Validation errors
   - User-friendly messages

---

## Styling Suggestions

- Use a modern UI framework (Tailwind CSS, Material-UI, Bootstrap)
- Add loading spinners
- Show success/error messages
- Responsive design
- Dark mode support (optional)

---

## Production Considerations

1. **Environment Variables**
   ```env
   REACT_APP_API_URL=http://localhost:8000
   ```

2. **CORS Configuration**
   - Update backend CORS to allow your frontend domain

3. **Error Handling**
   - Implement retry logic
   - Show user-friendly error messages

4. **Loading States**
   - Show progress for uploads
   - Show loading for queries

5. **Authentication** (if needed)
   - Add API key or token management

---

For complete API documentation, see `API_DOCUMENTATION.md`.

