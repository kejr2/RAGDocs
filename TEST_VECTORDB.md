# Vector DB Test Endpoints

Test endpoints for directly querying the vector database and inspecting semantic search results.

---

## Available Endpoints

### 1. Get Collections Info

Get information about vector database collections.

**Endpoint**: `GET /test/vectordb/collections/info`

**Response**:
```json
{
  "text_chunks": {
    "exists": true,
    "vector_size": 384,
    "points_count": 163
  },
  "code_chunks": {
    "exists": true,
    "vector_size": 768,
    "points_count": 15
  }
}
```

**Example**:
```bash
curl http://localhost:8000/test/vectordb/collections/info | jq '.'
```

---

### 2. Search Text Chunks

Direct semantic search in `text_chunks` collection.

**Endpoint**: `POST /test/vectordb/search/text`

**Request**:
```json
{
  "query": "What is FastAPI?",
  "doc_id": "optional_doc_id",
  "top_k": 10,
  "min_score": 0.3
}
```

**Response**:
```json
{
  "query": "What is FastAPI?",
  "collection": "text_chunks",
  "embedding_dim": 384,
  "total_results": 5,
  "results": [
    {
      "rank": 1,
      "distance": 0.234,
      "similarity_score": 0.81,
      "content": "FastAPI is a modern web framework...",
      "content_preview": "FastAPI is a modern web framework...",
      "content_length": 245,
      "metadata": {
        "chunk_id": "...",
        "doc_id": "...",
        "heading": "## What is FastAPI?",
        "type": "text"
      }
    }
  ],
  "query_embedding_sample": [0.123, -0.456, ...]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/test/vectordb/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "top_k": 5
  }' | jq '.'
```

---

### 3. Search Code Chunks

Direct semantic search in `code_chunks` collection.

**Endpoint**: `POST /test/vectordb/search/code`

**Request**: Same as text search

**Response**: Similar to text search, but includes `language` in metadata

**Example**:
```bash
curl -X POST http://localhost:8000/test/vectordb/search/code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to create an endpoint?",
    "top_k": 5
  }' | jq '.'
```

---

### 4. Compare Text vs Code Search

Compare results from both collections side-by-side.

**Endpoint**: `POST /test/vectordb/search/compare`

**Request**:
```json
{
  "query": "What is FastAPI?",
  "doc_id": "optional_doc_id",
  "top_k": 10
}
```

**Response**:
```json
{
  "query": "What is FastAPI?",
  "text_chunks": [...],
  "code_chunks": [...],
  "text_count": 5,
  "code_count": 2
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/test/vectordb/search/compare \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "top_k": 5
  }' | jq '.'
```

---

## Quick Test Script

Use the provided test script:

```bash
./test_vectordb.sh "What is FastAPI?" "DOC_ID_OPTIONAL"
```

This will:
1. Show collections info
2. Search text chunks
3. Search code chunks
4. Compare both collections

---

## Understanding the Results

### Distance vs Similarity Score

- **Distance**: Lower is better (0 = identical, 2 = opposite)
- **Similarity Score**: Higher is better (0 = not similar, 1 = identical)
  - Calculated as: `similarity = 1 / (1 + distance)`

### Relevance Thresholds

- **High relevance**: `similarity > 0.7` (distance < 0.43)
- **Medium relevance**: `similarity 0.5-0.7` (distance 0.43-1.0)
- **Low relevance**: `similarity < 0.5` (distance > 1.0)

### What to Look For

1. **Similarity Scores**: Check if results have high similarity (> 0.5)
2. **Content Preview**: Verify the content is relevant to your query
3. **Headings**: Check if headings match your query topic
4. **Compare Collections**: See which collection (text vs code) returns better results

---

## Example Workflow

### 1. Check Collections

```bash
curl http://localhost:8000/test/vectordb/collections/info | jq '.'
```

### 2. Search Text Collection

```bash
curl -X POST http://localhost:8000/test/vectordb/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to install?",
    "top_k": 5
  }' | jq '.results[] | {
    similarity_score,
    heading: .metadata.heading,
    content_preview
  }'
```

### 3. Search Code Collection

```bash
curl -X POST http://localhost:8000/test/vectordb/search/code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me code example",
    "top_k": 5
  }' | jq '.results[] | {
    similarity_score,
    language: .metadata.language,
    content_preview
  }'
```

### 4. Compare Both

```bash
curl -X POST http://localhost:8000/test/vectordb/search/compare \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this about?",
    "top_k": 5
  }' | jq '{
    query,
    text_best_score: .text_chunks[0].similarity_score,
    code_best_score: .code_chunks[0].similarity_score,
    which_better: (if .text_chunks[0].similarity_score > .code_chunks[0].similarity_score then "text" else "code" end)
  }'
```

---

## Debugging Tips

### If Results Seem Irrelevant

1. **Check similarity scores**: Should be > 0.3
2. **Try query enhancement**: The regular `/chat/query` endpoint uses LLM enhancement
3. **Adjust top_k**: Increase to get more candidates
4. **Check min_score**: Filter out low-relevance results

### If No Results

1. **Check collections exist**: Use `/test/vectordb/collections/info`
2. **Check document was uploaded**: Verify `doc_id` is correct
3. **Check content**: Make sure documents contain relevant information

### View Detailed Logs

```bash
docker compose logs -f backend | grep -E "(TEST|Search|similarity|distance)"
```

---

## Summary

**Available Test Endpoints:**

1. ✅ `GET /test/vectordb/collections/info` - Collection information
2. ✅ `POST /test/vectordb/search/text` - Search text chunks
3. ✅ `POST /test/vectordb/search/code` - Search code chunks
4. ✅ `POST /test/vectordb/search/compare` - Compare both collections

**What You Can See:**

- ✅ Raw vector search results
- ✅ Distance and similarity scores
- ✅ Full chunk content
- ✅ Metadata (headings, language, etc.)
- ✅ Embedding dimensions
- ✅ Context that will be sent to LLM

**Use Cases:**

- 🔍 Debug why certain queries don't return good results
- 📊 Compare text vs code search performance
- 🧪 Test embedding quality
- 📈 Analyze relevance scores
- 🔎 Inspect what context is being retrieved

