# Backend Startup Commands

Quick reference for starting the RAGDocs backend.

---

## Quick Start

### Start All Services (Docker Compose)

```bash
# Start all services (PostgreSQL, Qdrant, FastAPI backend)
docker compose up -d

# View logs
docker compose logs -f backend

# Check status
docker compose ps
```

---

## Detailed Commands

### 1. Start Services

```bash
# Start in detached mode (runs in background)
docker compose up -d

# Start with logs visible
docker compose up
```

### 2. Check Service Status

```bash
# List running containers
docker compose ps

# Check health endpoint
curl http://localhost:8000/health
```

### 3. View Logs

```bash
# View all logs
docker compose logs

# View backend logs only
docker compose logs backend

# Follow logs (real-time)
docker compose logs -f backend

# View last 100 lines
docker compose logs --tail=100 backend
```

### 4. Restart Services

```bash
# Restart all services
docker compose restart

# Restart only backend
docker compose restart backend

# Stop all services
docker compose stop

# Start stopped services
docker compose start
```

### 5. Stop Services

```bash
# Stop all services (keeps containers)
docker compose stop

# Stop and remove containers
docker compose down

# Stop and remove containers + volumes (deletes data)
docker compose down -v
```

### 6. Rebuild After Code Changes

```bash
# Rebuild and restart backend
docker compose build backend
docker compose up -d backend

# Or rebuild all services
docker compose build
docker compose up -d
```

---

## Service URLs

Once started, services are available at:

- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **PostgreSQL**: localhost:5433 (mapped from 5432)
- **Qdrant HTTP**: http://localhost:6333
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## First Time Setup

```bash
# 1. Start services
docker compose up -d

# 2. Wait for services to be ready (30-60 seconds)
# Watch logs to see when models are downloaded
docker compose logs -f backend

# 3. Check health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","gemini_enabled":true}
```

---

## Troubleshooting

### Services Not Starting

```bash
# Check what's wrong
docker compose ps
docker compose logs

# Check if ports are in use
lsof -i :8000
lsof -i :5433
lsof -i :6333
```

### Backend Not Responding

```bash
# Restart backend
docker compose restart backend

# Check logs for errors
docker compose logs backend | tail -n 50

# Rebuild if needed
docker compose build backend
docker compose up -d backend
```

### Port Conflicts

If ports are already in use:

1. **Stop conflicting services**
2. **Or modify ports in `docker-compose.yml`**:
   ```yaml
   ports:
     - "8001:8000"  # Change 8000 to 8001
   ```

---

## Complete Startup Sequence

```bash
# 1. Navigate to project root
cd /path/to/RAGDocs

# 2. Start all services
docker compose up -d

# 3. Wait for initialization (watch logs)
docker compose logs -f backend

# 4. Check health (wait for "Application startup complete")
curl http://localhost:8000/health

# 5. Verify Gemini is enabled
# Response should have "gemini_enabled": true
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services in background |
| `docker compose ps` | List running containers |
| `docker compose logs -f backend` | Follow backend logs |
| `docker compose restart backend` | Restart backend only |
| `docker compose down` | Stop and remove containers |
| `docker compose build backend` | Rebuild backend image |

---

## Environment Variables

The backend uses environment variables set in `docker-compose.yml`:

- `GEMINI_API_KEY`: Your Gemini API key
- `GEMINI_MODEL`: Model name (default: `gemini-2.5-flash`)
- Database and Qdrant connection settings (auto-configured)

To change settings, edit `docker-compose.yml` and restart:

```bash
docker compose down
docker compose up -d
```

---

## Development Mode

For local development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_USER=ragdocs
export POSTGRES_PASSWORD=ragdocs_password
export POSTGRES_DB=ragdocs_db
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export GEMINI_API_KEY=your_key_here
export GEMINI_MODEL=gemini-2.5-flash

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Note**: You'll need PostgreSQL and Qdrant running locally for this to work.

---

## Summary

**Most common command:**
```bash
docker compose up -d
```

**Verify it's running:**
```bash
curl http://localhost:8000/health
```

That's it! 🚀




