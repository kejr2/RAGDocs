# RAG API Testing Guide

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Python 3.8+** (for Python test script)
3. **curl** and **jq** (for bash script)

## Quick Start

### Step 1: Start the Backend

```bash
# Build and start the containers
docker compose up -d

# Check logs
docker compose logs -f backend

# Wait for the message: "Application startup complete"
```

### Step 2: Verify Service is Running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

---

## Testing Method 1: Python Script (Recommended)

### Install Dependencies

```bash
pip install requests
# Or use --user flag:
pip install --user requests
```

### Run the Test Suite

```bash
python3 test_api.py
```

This will:

- ✅ Check health endpoint
- ✅ Create and upload a sample FastAPI documentation
- ✅ Run 5 different query types
- ✅ Retrieve document chunks
- ✅ Display detailed results

---

## Testing Method 2: Bash Script

### Make Script Executable

```bash
chmod +x test_api.sh
```

### Run Tests

```bash
./test_api.sh
```

---

## Testing Method 3: Manual Testing with curl

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Upload a Document

Create a test document:

```bash
cat > test_doc.md << 'EOF'
# My Documentation

## Introduction

This is a test document.

## Code Example

```python
def hello():
    print("Hello World")
```
EOF
```

Upload it:

```bash
curl -X POST http://localhost:8000/docs/upload \
  -F "file=@test_doc.md"
```

Save the `doc_id` from the response!

### 3. Query the Document

Replace `YOUR_DOC_ID` with the actual doc_id:

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me the code example",
    "doc_id": "YOUR_DOC_ID",
    "top_k": 5
  }'
```

### 4. Get All Chunks

```bash
curl http://localhost:8000/docs/chunks/YOUR_DOC_ID
```

### 5. Query Without Doc ID (Search All Documents)

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this about?",
    "top_k": 5
  }'
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs/upload` | POST | Upload document |
| `/chat/query` | POST | Query documents |
| `/docs/chunks/{doc_id}` | GET | Get all chunks |
| `/docs/documents/{doc_id}` | DELETE | Delete document |

---

## Understanding the Response

### Upload Response:

```json
{
  "doc_id": "a1b2c3d4...",
  "filename": "test_doc.md",
  "total_chunks": 12,
  "text_chunks": 8,
  "code_chunks": 4,
  "status": "success"
}
```

### Query Response:

```json
{
  "answer": "Based on the retrieved context...",
  "sources": [
    {
      "content": "The actual text...",
      "metadata": {
        "chunk_id": "...",
        "doc_id": "...",
        "type": "code",
        "heading": "## Code Example",
        "language": "python"
      },
      "relevance_score": 0.89,
      "source_type": "code"
    }
  ],
  "context_used": ["chunk1", "chunk2", ...]
}
```

---

## Troubleshooting

### Error: Connection Refused

```bash
# Check if containers are running
docker compose ps

# Restart if needed
docker compose restart

# Check logs
docker compose logs backend
```

### Error: Models Not Downloaded

The first startup may take 2-3 minutes to download embedding models.

```bash
# Watch the download progress
docker compose logs -f backend
```

### Error: Out of Memory

If you see OOM errors:

```bash
# Check Docker memory allocation
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Recommended: At least 4GB for development
```

### Clear Database and Start Fresh

```bash
# Stop containers and remove volumes
docker compose down -v

# Restart
docker compose up -d
```

---

## Sample Test Queries

### Text Questions:

- "What is FastAPI?"
- "How do I get started?"
- "Explain the features"

### Code Questions:

- "Show me an example"
- "How to create an endpoint?"
- "Give me the installation code"

### Specific Questions:

- "How do I handle request bodies?"
- "What about async functions?"
- "Show path parameter examples"

---

## Code Verification

✅ **DocumentProcessor**: Exactly replicated with LangChain text splitters
✅ **PDFProcessor**: Exactly replicated with pypdf
✅ **HTMLProcessor**: Exactly replicated with BeautifulSoup
✅ **HybridRetriever**: Exactly replicated with reranking logic
✅ **QueryCache**: Exactly replicated with LFU eviction

**Note**: The original code used ChromaDB, but this implementation uses Qdrant for better scalability and production use. The core logic and structure remain identical.

---

## Next Steps

Once testing is successful:

1. ✅ Integrate with OpenAI API for better answers
2. ✅ Build the frontend UI
3. ✅ Add authentication
4. ✅ Deploy to production

