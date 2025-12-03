#!/bin/bash

# Debug Query Test Script
# Tests the debug endpoint to see LLM and embedding results

API_URL="http://localhost:8000"
QUERY="${1:-What is FastAPI?}"
DOC_ID="${2:-}"

echo "🧪 Testing Debug Endpoint"
echo "========================"
echo ""
echo "Query: $QUERY"
if [ -n "$DOC_ID" ]; then
    echo "Doc ID: $DOC_ID"
fi
echo ""

# Build request
REQUEST_BODY="{\"query\": \"$QUERY\", \"top_k\": 5"
if [ -n "$DOC_ID" ]; then
    REQUEST_BODY="$REQUEST_BODY, \"doc_id\": \"$DOC_ID\""
fi
REQUEST_BODY="$REQUEST_BODY}"

echo "📤 Sending debug request..."
echo ""

# Send request and save to file
curl -s -X POST "$API_URL/debug/query" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" | jq '.' > /tmp/debug_response.json

echo "✅ Response saved. Showing key information:"
echo ""

# Extract key information
echo "🔍 QUERY ENHANCEMENT:"
jq '.original_query, .enhanced_query, .keywords, .query_type' /tmp/debug_response.json
echo ""

echo "🧮 EMBEDDINGS:"
jq '.text_embedding_dim, .code_embedding_dim, .embeddings_generated' /tmp/debug_response.json
echo ""

echo "📊 RETRIEVAL RESULTS:"
jq '.text_search_results, .code_search_results, .total_results_before_filtering, .filtered_results' /tmp/debug_response.json
echo ""

echo "📈 RELEVANCE SCORES:"
jq '.relevance_scores' /tmp/debug_response.json
echo ""

echo "📝 CONTEXT SENT TO LLM:"
echo "----------------------"
jq -r '.context_sent_to_llm' /tmp/debug_response.json | head -n 30
echo "..."
echo ""

echo "🤖 LLM RESPONSE:"
echo "---------------"
jq -r '.llm_raw_response' /tmp/debug_response.json | head -n 40
echo "..."
echo ""

echo "✅ FINAL ANSWER:"
echo "---------------"
jq -r '.final_answer' /tmp/debug_response.json | head -n 40
echo ""

echo "📄 Full response saved to: /tmp/debug_response.json"
echo "View with: cat /tmp/debug_response.json | jq '.'"




