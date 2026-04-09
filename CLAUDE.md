# RAGDocs

RAG (Retrieval Augmented Generation) system for code documentation. Supports intelligent document querying with dual embedding models, LLM-powered query enhancement via Gemini AI, hybrid retrieval, and advanced reranking.

## Architecture

- **Backend**: FastAPI (Python 3.11) at `app/`
- **Frontend**: React + Vite + Tailwind CSS at `frontend/`
- **Vector DB**: Qdrant for semantic search
- **Metadata DB**: PostgreSQL via SQLAlchemy
- **LLM**: Google Gemini AI for query enhancement and answer generation
- **Embeddings**: Sentence Transformers (dual model — text + code)

## Development Commands

### Full Stack (Docker)
```bash
docker compose up -d          # Start all services
docker compose down           # Stop all services
docker compose logs -f        # Follow logs
```

Services:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Qdrant UI: http://localhost:6333/dashboard

### Backend
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload  # Dev server with hot reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # Dev server on port 3000
npm run build  # Production build
npm run lint   # ESLint check
```

### Testing
```bash
python3 test_api.py   # API integration tests
./test_api.sh         # Shell-based API tests
```

## Key Files

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry point |
| `app/core/config.py` | App configuration (env vars) |
| `app/core/database.py` | PostgreSQL connection setup |
| `app/core/qdrant_client.py` | Qdrant vector DB client |
| `app/services/` | Business logic (embeddings, retrieval, Gemini) |
| `app/api/` | Route handlers (chat, docs, chunks, health) |
| `app/models/document.py` | Pydantic data models |
| `frontend/src/App.jsx` | Main React component |
| `frontend/src/config.js` | API base URL config |
| `docker-compose.yml` | Full stack orchestration |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/docs/upload` | Upload and ingest a document |
| `POST` | `/chat/query` | RAG query with LLM response |
| `GET` | `/docs/chunks/{doc_id}` | Retrieve document chunks |
| `DELETE` | `/docs/documents/{doc_id}` | Delete a document |
| `GET` | `/health` | Health check |

## Environment Variables

Set in `docker-compose.yml` or a `.env` file:

```
GOOGLE_API_KEY=        # Gemini API key
DATABASE_URL=          # PostgreSQL connection string
QDRANT_HOST=           # Qdrant host (default: localhost)
QDRANT_PORT=           # Qdrant port (default: 6333)
```

## Embedding Models

- **Text**: `all-MiniLM-L6-v2`
- **Code**: `jinaai/jina-embeddings-v2-base-code`

Models are loaded at startup; first run will download them automatically.
