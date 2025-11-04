# Query Enhancement with LLM

## Overview

The RAGDocs system now uses **LLM-based query enhancement** to improve vector database retrieval. Before querying the vector database, the system uses Gemini AI to analyze and enhance user queries, making them more effective for semantic search.

---

## How It Works

### Flow Diagram

```
User Query
    ↓
LLM Query Enhancement (Gemini)
    ↓
Enhanced Query + Keywords + Concepts
    ↓
Vector Database Search (Qdrant)
    ↓
Better Retrieval Results
    ↓
Answer Generation
```

### Step-by-Step Process

1. **User submits query**: "What is FastAPI?"
2. **LLM enhancement**:
   - Analyzes the query
   - Generates enhanced query: "FastAPI definition overview introduction what is FastAPI"
   - Extracts keywords: ["FastAPI", "definition", "overview", "web framework"]
   - Identifies concepts: ["FastAPI", "Python web framework", "API framework"]
   - Detects query type: "definition"
3. **Vector search** uses enhanced query for better semantic matching
4. **Retrieval** finds more relevant chunks
5. **Answer generation** with better context

---

## Benefits

### 1. **Better Semantic Matching**
- Original: "what is fastapi?"
- Enhanced: "FastAPI definition overview introduction what is FastAPI web framework"

### 2. **Keyword Expansion**
- Adds synonyms: "API" → "endpoint", "route", "API endpoint"
- Adds related terms: "FastAPI" → "Python web framework", "async framework"

### 3. **Context-Aware Queries**
- "How to create endpoint" → "FastAPI endpoint creation steps tutorial example code"
- "Error handling" → "FastAPI error handling exception HTTPException status code"

### 4. **Query Type Detection**
- Definition queries: Boost heading matches like "## What is X?"
- How-to queries: Prioritize tutorial and example chunks
- Code queries: Emphasize code blocks and examples

---

## Implementation

### Service: `app/services/query_enhancer.py`

**Main Class**: `QueryEnhancer`

**Key Methods**:
- `enhance_query()`: Main method that uses LLM to enhance queries
- `get_search_queries()`: Generates multiple queries for multi-query retrieval
- `build_hybrid_search_query()`: Combines original and enhanced terms

### Integration: `app/api/chat.py`

Query enhancement happens before vector search:

```python
# Step 1: Enhance query
enhanced_data = query_enhancer.enhance_query(request.query)

# Step 2: Build hybrid search query
hybrid_search_query = query_enhancer.build_hybrid_search_query(
    enhanced_data, 
    request.query
)

# Step 3: Use enhanced query for vector search
text_embedding = embedding_service.encode_text([hybrid_search_query])[0]
code_embedding = embedding_service.encode_code([hybrid_search_query])[0]
```

---

## Enhanced Query Data Structure

```python
{
    "enhanced_query": "FastAPI definition overview introduction what is FastAPI",
    "keywords": ["FastAPI", "definition", "overview", "web", "framework"],
    "synonyms": ["API framework", "Python framework", "async framework"],
    "concepts": ["FastAPI", "Python web framework", "API development"],
    "query_type": "definition",  # definition|how-to|example|comparison|troubleshooting|general
    "search_strategy": "broad",  # broad|specific|hybrid
    "reasoning": "Expanded 'what is' query to include definition-related terms"
}
```

---

## Query Type Detection

The LLM identifies query types and adjusts search strategy:

| Query Type | Example | Search Strategy |
|-----------|---------|-----------------|
| **Definition** | "What is FastAPI?" | Broad, prioritize heading matches |
| **How-to** | "How to create endpoint?" | Hybrid, prioritize tutorial/example chunks |
| **Example** | "Show me FastAPI example" | Specific, prioritize code chunks |
| **Comparison** | "FastAPI vs Flask" | Broad, find comparison sections |
| **Troubleshooting** | "Error handling in FastAPI" | Specific, prioritize error-related chunks |
| **General** | "FastAPI features" | Hybrid, balanced search |

---

## Examples

### Example 1: Definition Query

**Original Query**: "What is FastAPI?"

**Enhanced Query**:
```json
{
    "enhanced_query": "FastAPI definition overview introduction what is FastAPI Python web framework",
    "keywords": ["FastAPI", "definition", "overview", "introduction", "web", "framework"],
    "synonyms": ["Python API framework", "async web framework", "modern framework"],
    "concepts": ["FastAPI", "Python web framework", "API framework", "web development"],
    "query_type": "definition",
    "search_strategy": "broad"
}
```

**Result**: Better matches for headings like "## What is FastAPI?" and introduction sections.

---

### Example 2: How-to Query

**Original Query**: "How to create POST endpoint?"

**Enhanced Query**:
```json
{
    "enhanced_query": "FastAPI POST endpoint creation steps tutorial guide example code request body",
    "keywords": ["POST", "endpoint", "creation", "steps", "tutorial", "example"],
    "synonyms": ["API route", "HTTP POST", "create endpoint", "endpoint definition"],
    "concepts": ["POST endpoint", "FastAPI routing", "request handling", "API creation"],
    "query_type": "how-to",
    "search_strategy": "hybrid"
}
```

**Result**: Prioritizes tutorial chunks and code examples with POST endpoints.

---

### Example 3: Code Query

**Original Query**: "Show me FastAPI code example"

**Enhanced Query**:
```json
{
    "enhanced_query": "FastAPI code example snippet implementation sample Python code",
    "keywords": ["FastAPI", "code", "example", "snippet", "implementation"],
    "synonyms": ["sample code", "code example", "example implementation"],
    "concepts": ["FastAPI code", "Python code example", "API implementation"],
    "query_type": "example",
    "search_strategy": "specific"
}
```

**Result**: Emphasizes code chunks and examples.

---

## Performance Considerations

### Latency
- Query enhancement adds ~200-500ms (LLM call)
- Improves retrieval quality significantly
- Overall better user experience despite slight delay

### Caching
- Consider caching enhanced queries for common questions
- Can reduce LLM calls for repeated queries

### Fallback
- If Gemini fails, falls back to simple keyword extraction
- System remains functional even if enhancement fails

---

## Configuration

### Enable/Disable
Query enhancement is automatically enabled if:
- `gemini_service.enabled == True`
- Gemini API key is configured

### Disable Enhancement
If you want to disable query enhancement, modify `app/services/query_enhancer.py`:

```python
def enhance_query(self, original_query: str, context: Optional[str] = None):
    # Skip enhancement
    return {
        "enhanced_query": original_query,
        "keywords": [],
        "synonyms": [],
        "concepts": [],
        "query_type": "general",
        "search_strategy": "broad"
    }
```

---

## Testing

### Test Query Enhancement

```bash
# Query with enhancement (automatic)
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "top_k": 5
  }' | jq '.'
```

Check backend logs to see:
- Original query
- Enhanced query
- Keywords extracted
- Query type detected

---

## Future Enhancements

### Multi-Query Retrieval
Use multiple enhanced queries and combine results:
```python
queries = query_enhancer.get_search_queries(enhanced_data)
# Search with each query and combine results
```

### Query Rewriting Based on Retrieved Context
1. Retrieve initial results
2. Analyze retrieved chunks
3. Rewrite query based on context
4. Re-search with refined query

### Query Expansion with Domain Knowledge
- Add domain-specific synonyms
- Expand technical terms
- Include acronyms and full forms

---

## Summary

Query enhancement with LLM:
- ✅ Improves retrieval quality
- ✅ Better semantic matching
- ✅ Keyword expansion
- ✅ Context-aware queries
- ✅ Query type detection
- ✅ Fallback mechanism

The system now uses **LLM → Vector DB → LLM** pipeline:
1. **LLM enhances query** (this document)
2. **Vector DB searches** (semantic similarity)
3. **LLM generates answer** (context-aware response)

This creates a more intelligent and accurate RAG system!

