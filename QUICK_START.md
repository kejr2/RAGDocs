# Quick Start Guide

## Run Tests (Easiest Methods)

### Method 1: Bash Script (No Python Setup Required)

```bash
# Make sure jq is installed (for JSON formatting)
brew install jq  # On macOS

# Run the test
./test_api.sh
```

### Method 2: Python Script (After Setup)

```bash
# First time setup
./setup_test_env.sh

# Activate environment and run
source test_venv/bin/activate
python3 test_api.py
```

### Method 3: Manual curl Commands

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Upload document
curl -X POST http://localhost:8000/docs/upload -F "file=@sample_fastapi_doc.md"

# 3. Query (use doc_id from upload response)
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is FastAPI?", "doc_id": "YOUR_DOC_ID", "top_k": 5}'
```

## Troubleshooting

**If Python script fails:**
- Use the bash script instead: `./test_api.sh`
- Or setup virtual env: `./setup_test_env.sh`

**If bash script fails:**
- Install jq: `brew install jq`
- Or view raw JSON: remove `| jq '.'` from commands

## All Endpoints

- `GET /health` - Health check
- `POST /docs/upload` - Upload document
- `POST /chat/query` - Query documents
- `GET /docs/chunks/{doc_id}` - Get document chunks
- `DELETE /docs/documents/{doc_id}` - Delete document

