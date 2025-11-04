#!/bin/bash

# Test Vector DB Endpoints
# Test semantic search directly on vector database

API_URL="http://localhost:8000"

echo "🧪 Vector DB Test Script"
echo "========================"
echo ""

# Test 1: Get Collections Info
echo "📊 Test 1: Get Collections Info"
echo "-------------------------------"
curl -s "$API_URL/test/vectordb/collections/info" | jq '.'
echo ""
echo ""

# Test 2: Search Text Chunks
echo "📝 Test 2: Search Text Chunks"
echo "------------------------------"
QUERY="${1:-What is FastAPI?}"
DOC_ID="${2:-}"

if [ -n "$DOC_ID" ]; then
    REQUEST_BODY="{\"query\": \"$QUERY\", \"doc_id\": \"$DOC_ID\", \"top_k\": 5}"
else
    REQUEST_BODY="{\"query\": \"$QUERY\", \"top_k\": 5}"
fi

curl -s -X POST "$API_URL/test/vectordb/search/text" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" | jq '{
    query,
    collection,
    embedding_dim,
    total_results,
    results: [.results[] | {
      rank,
      similarity_score,
      distance,
      heading: .metadata.heading,
      content_preview
    }]
  }'
echo ""
echo ""

# Test 3: Search Code Chunks
echo "💻 Test 3: Search Code Chunks"
echo "------------------------------"
curl -s -X POST "$API_URL/test/vectordb/search/code" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" | jq '{
    query,
    collection,
    embedding_dim,
    total_results,
    results: [.results[] | {
      rank,
      similarity_score,
      distance,
      language: .metadata.language,
      heading: .metadata.heading,
      content_preview
    }]
  }'
echo ""
echo ""

# Test 4: Compare Both Collections
echo "⚖️  Test 4: Compare Text vs Code Search"
echo "-----------------------------------------"
curl -s -X POST "$API_URL/test/vectordb/search/compare" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" | jq '{
    query,
    text_count,
    code_count,
    text_chunks: [.text_chunks[] | {
      rank,
      similarity_score,
      heading,
      content_preview: .content_preview
    }],
    code_chunks: [.code_chunks[] | {
      rank,
      similarity_score,
      language,
      heading,
      content_preview: .content_preview
    }]
  }'
echo ""
echo ""

echo "✅ Tests Complete!"
echo ""
echo "💡 Tips:"
echo "  - View backend logs for detailed output: docker compose logs -f backend"
echo "  - Check similarity scores (higher = more relevant)"
echo "  - Compare text vs code results to see which collection is better for your query"

