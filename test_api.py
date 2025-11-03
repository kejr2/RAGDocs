import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint with Gemini status"""
    print("=" * 60)
    print("Testing Health Check...")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print()
        
        # Check Gemini status
        if data.get('gemini_enabled'):
            print("✅ Gemini AI is ENABLED - AI-generated answers will be used")
        else:
            print("⚠️  Gemini AI is DISABLED - Basic formatting will be used")
        print()
        
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_upload_document(file_path):
    """Test document upload"""
    print("=" * 60)
    print("Testing Document Upload...")
    print("=" * 60)
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f, 'text/plain')}
        response = requests.post(f"{BASE_URL}/docs/upload", files=files)
    
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    print()
    
    if response.status_code == 201:
        print(f"✅ Document processed:")
        print(f"   - Total chunks: {result.get('total_chunks')}")
        print(f"   - Text chunks: {result.get('text_chunks')}")
        print(f"   - Code chunks: {result.get('code_chunks')}")
        return result.get('doc_id')
    return None

def test_query(query_text, doc_id=None, top_k=5, expected_features=None):
    """Test query endpoint with enhanced output"""
    print("=" * 60)
    print(f"Testing Query: '{query_text}'")
    print("=" * 60)
    
    if doc_id:
        print(f"📄 Document ID: {doc_id}")
    else:
        print("🌐 Global Search (all documents)")
    
    payload = {
        "query": query_text,
        "doc_id": doc_id,
        "top_k": top_k
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/chat/query",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    elapsed_time = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {elapsed_time:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        
        # Check if answer is from Gemini (AI-generated) or fallback
        answer = result.get('answer', '')
        is_ai_generated = (
            len(answer) > 200 or  # Longer answers usually from AI
            'Based on the provided' in answer or  # Gemini pattern
            'However' in answer or  # Gemini explanation pattern
            '\n\n' in answer  # Multi-paragraph
        )
        
        print(f"\n🤖 Answer Source: {'Gemini AI' if is_ai_generated else 'Basic Formatting'}")
        print(f"\n📝 Answer ({len(answer)} chars):")
        print("-" * 60)
        # Show first 400 chars or full answer if shorter
        answer_preview = answer[:400] + "..." if len(answer) > 400 else answer
        print(answer_preview)
        print("-" * 60)
        
        sources = result.get('sources', [])
        print(f"\n📚 Sources Retrieved: {len(sources)}")
        
        # Analyze sources
        text_sources = [s for s in sources if s['metadata'].get('type') == 'text']
        code_sources = [s for s in sources if s['metadata'].get('type') == 'code']
        
        print(f"   - Text chunks: {len(text_sources)}")
        print(f"   - Code chunks: {len(code_sources)}")
        
        # Check for definition chunks (especially for "what is" questions)
        definition_questions = ["what is", "what are", "define", "explain"]
        if any(q in query_text.lower() for q in definition_questions):
            definition_chunks = [
                s for s in sources 
                if any(keyword in s['metadata'].get('heading', '').lower() 
                       for keyword in ['what is', 'what are', 'definition', 'introduction', 'overview'])
            ]
            if definition_chunks:
                print(f"   ✅ Found definition chunk(s): {len(definition_chunks)}")
                for i, def_chunk in enumerate(definition_chunks[:2], 1):
                    print(f"      {i}. {def_chunk['metadata'].get('heading', 'N/A')} (relevance: {def_chunk.get('relevance_score', 0):.3f})")
            else:
                print(f"   ⚠️  No definition chunks found in top results")
        
        print("\n📊 Top 3 Sources:")
        for i, source in enumerate(sources[:3], 1):
            print(f"\n  Source {i}:")
            print(f"    Type: {source['metadata'].get('type', 'unknown')}")
            print(f"    Heading: {source['metadata'].get('heading', 'N/A')[:50]}")
            print(f"    Relevance: {source.get('relevance_score', 0):.3f}")
            content_preview = source['content'][:80].replace('\n', ' ')
            print(f"    Content: {content_preview}...")
            if source['metadata'].get('language'):
                print(f"    Language: {source['metadata'].get('language')}")
        
        # Verify context includes headings
        context_used = result.get('context_used', [])
        headings_in_context = sum(1 for ctx in context_used if ctx.startswith('#'))
        if headings_in_context > 0:
            print(f"\n✅ Context includes headings: {headings_in_context} chunk(s) have headings")
        
        # Expected features check
        if expected_features:
            print(f"\n🔍 Feature Checks:")
            for feature, check_func in expected_features.items():
                result_check = check_func(result)
                status = "✅" if result_check else "❌"
                print(f"   {status} {feature}: {result_check}")
        
    else:
        print(f"Error: {response.text}")
    print()

def test_get_chunks(doc_id):
    """Test retrieving document chunks with detailed analysis"""
    print("=" * 60)
    print("Testing Get Document Chunks...")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/docs/chunks/{doc_id}")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Total Chunks: {result['total_chunks']}")
        
        chunks = result.get('chunks', [])
        
        # Analyze chunk types
        text_chunks = [c for c in chunks if c['metadata'].get('type') == 'text']
        code_chunks = [c for c in chunks if c['metadata'].get('type') == 'code']
        
        print(f"   - Text chunks: {len(text_chunks)}")
        print(f"   - Code chunks: {len(code_chunks)}")
        
        # Check for headings
        chunks_with_headings = [c for c in chunks if c['metadata'].get('heading')]
        print(f"   - Chunks with headings: {len(chunks_with_headings)}")
        
        # Show chunk distribution by heading
        heading_counts = {}
        for chunk in chunks:
            heading = chunk['metadata'].get('heading', 'No heading')
            heading_counts[heading] = heading_counts.get(heading, 0) + 1
        
        print(f"\n📑 Chunks by Section:")
        for heading, count in sorted(heading_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {heading[:50]}: {count} chunk(s)")
        
        print(f"\n📄 First 3 Chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n  Chunk {i}:")
            print(f"    Type: {chunk['metadata'].get('type', 'unknown')}")
            print(f"    Heading: {chunk['metadata'].get('heading', 'N/A')[:60]}")
            content_preview = chunk['content'][:100].replace('\n', ' ')
            print(f"    Content: {content_preview}...")
    else:
        print(f"Error: {response.text}")
    print()

def test_delete_document(doc_id):
    """Test document deletion"""
    print("=" * 60)
    print("Testing Document Deletion...")
    print("=" * 60)
    
    response = requests.delete(f"{BASE_URL}/docs/documents/{doc_id}")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print(f"✅ Document {doc_id} deleted successfully")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_global_query(query_text, top_k=5):
    """Test query without doc_id (searches all documents)"""
    print("=" * 60)
    print(f"Testing Global Query (All Documents): '{query_text}'")
    print("=" * 60)
    
    payload = {
        "query": query_text,
        "top_k": top_k
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/query",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        sources = result.get('sources', [])
        
        # Group by document
        docs_found = {}
        for source in sources:
            doc_id = source['metadata'].get('doc_id', 'unknown')
            if doc_id not in docs_found:
                docs_found[doc_id] = []
            docs_found[doc_id].append(source)
        
        print(f"\n📚 Found results from {len(docs_found)} document(s):")
        for doc_id, doc_sources in docs_found.items():
            print(f"   - Doc ID: {doc_id[:16]}... ({len(doc_sources)} chunks)")
        
        print(f"\nTotal Sources: {len(sources)}")
        print(f"Answer Preview: {result.get('answer', '')[:200]}...")
    else:
        print(f"Error: {response.text}")
    print()

def create_sample_document():
    """Create a sample markdown document for testing"""
    sample_content = """# FastAPI Documentation

## What is FastAPI?

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.

The key features are:

- Fast: Very high performance, on par with NodeJS and Go
- Fast to code: Increase the speed to develop features by about 200% to 300%
- Fewer bugs: Reduce about 40% of human (developer) induced errors
- Intuitive: Great editor support with completion everywhere
- Easy: Designed to be easy to use and learn
- Short: Minimize code duplication
- Robust: Get production-ready code
- Standards-based: Based on (and fully compatible with) open standards for APIs: OpenAPI and JSON Schema

## Installation

To install FastAPI, you need to install it along with an ASGI server:

```bash
pip install fastapi
pip install "uvicorn[standard]"
```

## Creating Your First API

Here's a simple example of creating a FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## Running the Application

To run your FastAPI application:

```bash
uvicorn main:app --reload
```

The `--reload` flag makes the server restart after code changes. Use it only for development.

## Path Parameters

FastAPI supports path parameters with type hints:

```python
@app.get("/users/{user_id}")
async def read_user(user_id: int):
    return {"user_id": user_id}
```

## Query Parameters

Query parameters are the key-value pairs that go after the `?` in a URL:

```python
@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## Request Body

To declare a request body, you use Pydantic models:

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items/")
async def create_item(item: Item):
    return item
```

## Automatic Documentation

FastAPI automatically generates interactive API documentation. After running your app, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Validation

FastAPI provides automatic validation using Pydantic:

```python
from typing import Optional
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
```

## Conclusion

FastAPI makes it easy to build APIs quickly with automatic documentation, validation, and high performance.

"""
    
    with open('sample_fastapi_doc.md', 'w') as f:
        f.write(sample_content)
    
    print("✅ Created sample document: sample_fastapi_doc.md")
    return 'sample_fastapi_doc.md'

def run_full_test():
    """Run complete enhanced test suite"""
    print("\n" + "=" * 60)
    print("🚀 ENHANCED RAG API TEST SUITE")
    print("=" * 60 + "\n")
    
    # Step 1: Health check with Gemini status
    health_data = test_health()
    if not health_data:
        print("❌ Health check failed. Is the server running?")
        print("Start with: docker compose up -d")
        return
    
    gemini_enabled = health_data.get('gemini_enabled', False)
    print(f"✅ Health check passed!")
    if gemini_enabled:
        print("✨ Gemini AI is enabled - expect AI-generated answers\n")
    else:
        print("⚠️  Gemini AI is disabled - basic formatting will be used\n")
    time.sleep(1)
    
    # Step 2: Create and upload sample document
    sample_file = create_sample_document()
    print()
    time.sleep(1)
    
    doc_id = test_upload_document(sample_file)
    if not doc_id:
        print("❌ Document upload failed!")
        return
    
    time.sleep(2)  # Wait for processing
    
    # Step 3: Test definition questions (verify context retrieval)
    print("\n" + "=" * 60)
    print("📖 TESTING DEFINITION QUESTIONS")
    print("=" * 60 + "\n")
    
    definition_queries = [
        ("What is FastAPI?", {
            "definition_chunk_found": lambda r: any(
                "what is" in s['metadata'].get('heading', '').lower() 
                or "introduction" in s['metadata'].get('heading', '').lower()
                for s in r.get('sources', [])
            ),
            "ai_answer_quality": lambda r: len(r.get('answer', '')) > 100 and 
                                          ("FastAPI" in r.get('answer', '') or 
                                           "web framework" in r.get('answer', '').lower())
        }),
    ]
    
    for query, checks in definition_queries:
        test_query(query, doc_id=doc_id, top_k=5, expected_features=checks)
        time.sleep(1)
    
    # Step 4: Test different query types
    print("\n" + "=" * 60)
    print("🔍 TESTING VARIOUS QUERY TYPES")
    print("=" * 60 + "\n")
    
    test_queries = [
        ("How do I install FastAPI?", "Installation"),
        ("Show me code example for path parameters", "Code Example"),
        ("What are the features of FastAPI?", "Features"),
        ("How to create a POST endpoint with request body?", "Code Example"),
        ("Explain query parameters", "Explanation"),
    ]
    
    for query, category in test_queries:
        print(f"\n📝 Category: {category}")
        test_query(query, doc_id=doc_id, top_k=5)
        time.sleep(1)
    
    # Step 5: Test hybrid search (verify both text and code chunks retrieved)
    print("\n" + "=" * 60)
    print("🔄 TESTING HYBRID SEARCH")
    print("=" * 60 + "\n")
    
    hybrid_query = "How do I create an API with FastAPI? Show me the code and explain it."
    test_query(
        hybrid_query, 
        doc_id=doc_id, 
        top_k=5,
        expected_features={
            "text_chunks_retrieved": lambda r: len([s for s in r.get('sources', []) if s['metadata'].get('type') == 'text']) > 0,
            "code_chunks_retrieved": lambda r: len([s for s in r.get('sources', []) if s['metadata'].get('type') == 'code']) > 0,
            "headings_in_context": lambda r: any(ctx.startswith('#') for ctx in r.get('context_used', []))
        }
    )
    
    # Step 6: Get all chunks with analysis
    print("\n" + "=" * 60)
    print("📚 TESTING CHUNK RETRIEVAL")
    print("=" * 60 + "\n")
    
    test_get_chunks(doc_id)
    
    # Step 7: Test global query (without doc_id)
    print("\n" + "=" * 60)
    print("🌐 TESTING GLOBAL SEARCH")
    print("=" * 60 + "\n")
    
    test_global_query("What is FastAPI?", top_k=3)
    
    # Step 8: Test delete functionality
    print("\n" + "=" * 60)
    print("🗑️  TESTING DOCUMENT DELETION")
    print("=" * 60 + "\n")
    
    # Ask user if they want to delete
    print(f"Document ID to delete: {doc_id}")
    print("⚠️  Skip deletion test to keep document for further testing")
    print("(You can manually test: DELETE /docs/documents/{doc_id})\n")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 TEST SUITE COMPLETED!")
    print("=" * 60 + "\n")
    
    print("📊 Test Summary:")
    print(f"   ✅ Health check: PASSED")
    print(f"   ✅ Document upload: PASSED")
    print(f"   ✅ Definition questions: TESTED")
    print(f"   ✅ Various query types: TESTED")
    print(f"   ✅ Hybrid search: TESTED")
    print(f"   ✅ Chunk retrieval: TESTED")
    print(f"   ✅ Global search: TESTED")
    print(f"\n📄 Document ID for manual testing: {doc_id}")
    print(f"\n💡 To delete the document:")
    print(f"   curl -X DELETE http://localhost:8000/docs/documents/{doc_id}")

if __name__ == "__main__":
    try:
        run_full_test()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server!")
        print("\n💡 Make sure the backend is running:")
        print("   1. docker compose up -d")
        print("   2. Wait a few seconds for the server to start")
        print("   3. Run this script again")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
