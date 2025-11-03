# Gemini AI Integration Guide

## Overview

This RAG system now integrates with Google's Gemini AI to generate intelligent, context-aware answers from your documentation.

## Setup Instructions

### Step 1: Get Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### Step 2: Configure API Key

**Option A: Using .env file (Recommended)**

1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   GEMINI_MODEL=gemini-pro
   ```

**Option B: Environment Variable**

```bash
export GEMINI_API_KEY=your_actual_api_key_here
export GEMINI_MODEL=gemini-pro
```

**Option C: Docker Compose**

Add to `docker-compose.yml` or pass as environment variable:
```bash
GEMINI_API_KEY=your_key docker compose up
```

### Step 3: Verify Setup

1. Start the services:
   ```bash
   docker compose up -d
   ```

2. Check health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-11-02T...",
     "gemini_enabled": true
   }
   ```

3. Check backend logs:
   ```bash
   docker compose logs backend | grep Gemini
   ```

   Should see:
   ```
   ✅ Gemini API initialized with model: gemini-pro
   ```

## How It Works

### With Gemini Enabled

When you query the system:
1. Documents are retrieved using hybrid search
2. Context is built from retrieved chunks
3. **Gemini AI generates intelligent answer** based on context
4. Answer includes proper code formatting and structure

### Without Gemini (Fallback)

If Gemini is not configured:
- System uses basic answer formatting
- Still returns relevant sources
- Less intelligent but functional

## Testing

### Test Query Endpoint

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I install FastAPI?",
    "doc_id": "your_doc_id",
    "top_k": 5
  }'
```

### Expected Behavior

**With Gemini:**
- Answer is well-structured
- Code examples properly formatted
- Context-aware explanations

**Without Gemini:**
- Basic formatting
- Still shows relevant sources
- Functional but simpler

## Troubleshooting

### "⚠️ WARNING: GEMINI_API_KEY not found"

**Solution:** 
- Make sure `.env` file exists in project root
- Check that `GEMINI_API_KEY` is set in `.env`
- Restart Docker containers: `docker compose restart backend`

### "Gemini API error: ..."

**Common Causes:**
1. **Invalid API Key** - Check your key is correct
2. **Quota Exceeded** - Check your Google AI Studio quota
3. **Rate Limiting** - Wait and retry

**Solution:**
- Verify API key in [Google AI Studio](https://makersuite.google.com/app/apikey)
- Check usage limits
- System will automatically fallback to basic formatting

### Docker Container Not Picking Up .env

**Solution:**
- Make sure `.env` is in project root (same directory as `docker-compose.yml`)
- Restart containers: `docker compose down && docker compose up -d`
- Check logs: `docker compose logs backend`

## Available Models

Default: `gemini-pro`

Other options:
- `gemini-pro` - Standard model (recommended)
- `gemini-pro-vision` - For multimodal (if needed)

Change in `.env`:
```bash
GEMINI_MODEL=gemini-pro
```

## Security Notes

⚠️ **Important:**

1. **Never commit `.env` file to git**
   - `.env` is in `.gitignore` (should be)
   - Commit `.env.example` instead

2. **Production:**
   - Use secret management (AWS Secrets Manager, etc.)
   - Don't hardcode API keys
   - Use environment variables or secure vaults

3. **API Key Limits:**
   - Free tier has usage limits
   - Monitor usage in [Google AI Studio](https://makersuite.google.com/app/apikey)

## Integration Details

### Files Modified

1. **`app/services/gemini.py`** - Gemini service
2. **`app/services/answer_formatter.py`** - Fallback formatter
3. **`app/api/chat.py`** - Query endpoint with Gemini
4. **`app/api/health.py`** - Health check with Gemini status
5. **`app/core/config.py`** - Added Gemini settings
6. **`requirements.txt`** - Added `google-generativeai`
7. **`docker-compose.yml`** - Added environment variables

### Code Flow

```
Query Request
    ↓
Retrieve Documents (Qdrant)
    ↓
Build Context
    ↓
Generate Answer (Gemini) OR Format Basic Answer
    ↓
Return Response
```

## Next Steps

1. ✅ Add API key to `.env`
2. ✅ Restart services
3. ✅ Test queries
4. 🚀 Enjoy intelligent answers!

