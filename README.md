# RAGDocs - RAG System for Documentation and Code

A RAG (Retrieval-Augmented Generation) system designed to handle documentation and code with enhanced code retrieval capabilities.

## Phase 1: Core Infrastructure ✅

This phase sets up the core infrastructure with Docker Compose, FastAPI backend, PostgreSQL, and Qdrant.

### Features

- **FastAPI Backend**: RESTful API with automatic documentation
- **PostgreSQL**: Metadata storage for documents and indexing information
- **Qdrant**: Vector database for semantic search
- **Health Check Endpoint**: Verify system status
- **Connection Retry Logic**: Robust database and vector store connections
- **Stub Endpoints**: `/docs/upload` and `/chat/query` ready for implementation

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)

### Quick Start

1. **Clone the repository** (if applicable) or navigate to the project directory

2. **Start all services with Docker Compose:**
   ```bash
   docker compose up -d
   ```

3. **Verify the services are running:**
   ```bash
   docker compose ps
   ```

4. **Check the health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```
   
   Expected response:
   ```json
   {"status": "ok"}
   ```

5. **Access API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Services

- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Qdrant HTTP API**: http://localhost:6333
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### Project Structure

```
RAGDocs/
├── app/
│   ├── api/
│   │   ├── health.py      # Health check endpoint
│   │   ├── docs.py        # Document upload endpoint (stub)
│   │   └── chat.py        # Chat query endpoint (stub)
│   ├── core/
│   │   ├── config.py      # Configuration settings
│   │   ├── database.py    # PostgreSQL connection and retry logic
│   │   └── qdrant_client.py  # Qdrant connection and retry logic
│   └── main.py            # FastAPI application
├── docker-compose.yml     # Docker services configuration
├── Dockerfile             # Backend container definition
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### API Endpoints

#### Health Check
- **GET** `/health`
  - Returns: `{"status": "ok"}`

#### Document Upload (Stub)
- **POST** `/docs/upload`
  - Accepts: Multipart file upload
  - Returns: Confirmation message (stub)

#### Chat Query (Stub)
- **POST** `/chat/query`
  - Body: `{"query": "your question"}`
  - Returns: Stub response (to be implemented)

### Data Persistence

PostgreSQL and Qdrant data are stored in Docker volumes:
- `postgres_data`: PostgreSQL database files
- `qdrant_data`: Qdrant vector database files

These volumes persist across container restarts. To reset:
```bash
docker compose down -v
```

### Development

For local development without Docker:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables** (or use .env file):
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_USER=ragdocs
   export POSTGRES_PASSWORD=ragdocs_password
   export POSTGRES_DB=ragdocs_db
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   export QDRANT_GRPC_PORT=6334
   ```

3. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing Phase 1

1. ✅ `docker compose up` works
2. ✅ `GET localhost:8000/health` → `{"status": "ok"}`
3. ✅ Qdrant and Postgres volumes persist after restart:
   ```bash
   docker compose down
   docker compose up -d
   # Verify data still exists
   ```

### Next Steps (Future Phases)

- Phase 2: Document processing and parsing (PDF, API docs, code files)
- Phase 3: Enhanced code chunking and embedding strategies
- Phase 4: RAG query processing and retrieval
- Phase 5: UI for document upload and chat interface

### Troubleshooting

**Port already in use:**
- Change ports in `docker-compose.yml` if 8000, 5432, or 6333 are taken

**Connection errors:**
- Ensure all services are healthy: `docker compose ps`
- Check logs: `docker compose logs backend`

**Reset everything:**
```bash
docker compose down -v
docker compose up -d
```

