#!/bin/bash

BASE_URL="http://localhost:8000"

echo "======================================"
echo "🚀 RAG API Testing Script"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
echo "GET $BASE_URL/health"
echo ""
curl -X GET "$BASE_URL/health" | jq '.'
echo -e "\n${GREEN}✓ Health check complete${NC}\n"

sleep 1

# Test 2: Create Sample Document
echo -e "${BLUE}Test 2: Creating Sample Document${NC}"
cat > sample_doc.md << 'EOF'
# Python FastAPI Guide

## What is FastAPI?

FastAPI is a modern, fast web framework for building APIs with Python 3.7+.

## Installation

Install FastAPI with:

```bash
pip install fastapi uvicorn
```

## Hello World Example

Create a file `main.py`:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

## Running the Server

Run with:

```bash
uvicorn main:app --reload
```

## Features

- Automatic interactive API documentation
- Data validation with Pydantic
- Async support
- Type hints everywhere

## Request Body Example

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

## Conclusion

FastAPI makes building APIs fast and easy!
EOF

echo -e "${GREEN}✓ Sample document created: sample_doc.md${NC}\n"

sleep 1

# Test 3: Upload Document
echo -e "${BLUE}Test 3: Upload Document${NC}"
echo "POST $BASE_URL/docs/upload"
echo ""
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/docs/upload" \
  -F "file=@sample_doc.md")

echo "$UPLOAD_RESPONSE" | jq '.'
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.doc_id')

echo ""
echo -e "${GREEN}✓ Document uploaded with ID: $DOC_ID${NC}\n"

sleep 2

# Test 4: Query - Text Question
echo -e "${BLUE}Test 4: Query - Text Question${NC}"
echo "Question: What is FastAPI?"
echo ""
curl -s -X POST "$BASE_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is FastAPI?",
    "doc_id": "'"$DOC_ID"'",
    "top_k": 5
  }' | jq '.'

echo -e "\n${GREEN}✓ Text query complete${NC}\n"

sleep 2

# Test 5: Query - Code Question
echo -e "${BLUE}Test 5: Query - Code Question${NC}"
echo "Question: Show me how to create a POST endpoint"
echo ""
curl -s -X POST "$BASE_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me how to create a POST endpoint with request body",
    "doc_id": "'"$DOC_ID"'",
    "top_k": 5
  }' | jq '.'

echo -e "\n${GREEN}✓ Code query complete${NC}\n"

sleep 2

# Test 6: Query - Installation Question
echo -e "${BLUE}Test 6: Query - Installation${NC}"
echo "Question: How do I install FastAPI?"
echo ""
curl -s -X POST "$BASE_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I install FastAPI?",
    "doc_id": "'"$DOC_ID"'",
    "top_k": 3
  }' | jq '.'

echo -e "\n${GREEN}✓ Installation query complete${NC}\n"

sleep 2

# Test 7: Get All Chunks
echo -e "${BLUE}Test 7: Retrieve Document Chunks${NC}"
echo "GET $BASE_URL/docs/chunks/$DOC_ID"
echo ""
curl -s -X GET "$BASE_URL/docs/chunks/$DOC_ID" | jq '{
  doc_id: .doc_id,
  total_chunks: .total_chunks,
  first_chunk_preview: .chunks[0].content[:100],
  chunk_types: [.chunks[].metadata.type] | group_by(.) | map({type: .[0], count: length})
}'

echo -e "\n${GREEN}✓ Chunks retrieved${NC}\n"

sleep 1

# Test 8: Query Without Doc ID (search all)
echo -e "${BLUE}Test 8: Query All Documents${NC}"
echo "Question: What are the features?"
echo ""
curl -s -X POST "$BASE_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the features of FastAPI?",
    "top_k": 5
  }' | jq '.sources | length as $count | {
  total_sources: $count,
  source_types: [.[].metadata.type] | unique
}'

echo -e "\n${GREEN}✓ Global query complete${NC}\n"

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}🎉 All Tests Completed!${NC}"
echo "======================================"
echo ""
echo "Endpoints tested:"
echo "  ✓ GET  /health"
echo "  ✓ POST /docs/upload"
echo "  ✓ POST /chat/query"
echo "  ✓ GET  /docs/chunks/{doc_id}"
echo ""
echo "Document ID: $DOC_ID"
echo ""
# Cleanup option
echo "Files created:"
echo "  - sample_doc.md"
echo ""
read -p "Delete test file? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    rm sample_doc.md
    echo -e "${GREEN}✓ Test file deleted${NC}"
fi

