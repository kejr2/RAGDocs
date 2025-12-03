#!/bin/bash

# ============================================
# Complete PDF Upload and Query Workflow
# ============================================

API_URL="http://localhost:8000"
PDF_FILE="$1"

if [ -z "$PDF_FILE" ]; then
    echo "Usage: ./test_pdf_commands.sh <path_to_pdf_file>"
    echo ""
    echo "Example: ./test_pdf_commands.sh document.pdf"
    exit 1
fi

if [ ! -f "$PDF_FILE" ]; then
    echo "Error: File '$PDF_FILE' not found"
    exit 1
fi

echo "============================================"
echo "Step 1: Upload PDF Document"
echo "============================================"
echo "Uploading: $PDF_FILE"
echo ""

UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/docs/upload" \
  -F "file=@$PDF_FILE")

echo "$UPLOAD_RESPONSE" | jq '.'

# Extract doc_id from response
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.doc_id')

if [ "$DOC_ID" == "null" ] || [ -z "$DOC_ID" ]; then
    echo ""
    echo "Error: Failed to upload PDF or extract doc_id"
    exit 1
fi

echo ""
echo "✅ Document uploaded successfully!"
echo "📄 Doc ID: $DOC_ID"
echo ""
echo "============================================"
echo "Waiting 2 seconds for processing..."
echo "============================================"
sleep 2

echo ""
echo "============================================"
echo "Step 2: Query the PDF (with doc_id)"
echo "============================================"
echo "Query: 'What is this document about?'"
echo ""

curl -s -X POST "$API_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"What is this document about?\",
    \"doc_id\": \"$DOC_ID\",
    \"top_k\": 5
  }" | jq '.'

echo ""
echo "============================================"
echo "Step 3: Query with specific question"
echo "============================================"
echo "Query: 'What are the main topics covered?'"
echo ""

curl -s -X POST "$API_URL/chat/query" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"What are the main topics covered?\",
    \"doc_id\": \"$DOC_ID\",
    \"top_k\": 5
  }" | jq '.answer'

echo ""
echo "============================================"
echo "✅ Complete! PDF uploaded and queried."
echo "============================================"
echo ""
echo "You can now query this PDF using doc_id: $DOC_ID"
echo "Or query all documents (omit doc_id)"




