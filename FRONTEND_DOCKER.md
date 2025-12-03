# Frontend Docker Setup

## Overview

The frontend is now containerized using Docker with a multi-stage build process:
1. **Build stage**: Uses Node.js to build the React application
2. **Production stage**: Uses Nginx to serve the static files

## Docker Compose

The frontend service is included in `docker-compose.yml`:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: ragdocs-frontend
  ports:
    - "3000:80"
  environment:
    - VITE_API_BASE_URL=http://localhost:8000
  depends_on:
    backend:
      condition: service_started
  restart: unless-stopped
```

## Configuration

### Environment Variables

- `VITE_API_BASE_URL`: Backend API URL (defaults to `http://localhost:8000` in development)

### Ports

- Frontend is accessible at `http://localhost:3000`
- Nginx listens on port 80 inside the container
- Port 3000 on host maps to port 80 in container

## Building and Running

### Start all services (including frontend)

```bash
docker compose up -d
```

### Build only the frontend

```bash
docker compose build frontend
```

### Rebuild frontend after changes

```bash
docker compose build --no-cache frontend
docker compose up -d frontend
```

### View frontend logs

```bash
docker compose logs -f frontend
```

### Stop frontend

```bash
docker compose stop frontend
```

## Development vs Production

### Development (Local)

Run the frontend locally with Vite:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` (or Vite's assigned port).

### Production (Docker)

The Docker container serves the built static files through Nginx:

```bash
docker compose up -d frontend
```

The frontend will be available at `http://localhost:3000`.

## File Structure

```
frontend/
├── Dockerfile          # Multi-stage Docker build
├── nginx.conf          # Nginx configuration
├── .dockerignore       # Files to exclude from Docker build
├── package.json
├── vite.config.js
└── src/
    ├── config.js       # API configuration
    └── ...
```

## Nginx Configuration

The `nginx.conf` includes:
- Gzip compression
- Security headers
- SPA routing support (React Router)
- Static asset caching
- CORS headers for API requests

## Troubleshooting

### Frontend can't connect to backend

1. Check that backend is running: `docker compose ps`
2. Verify API_BASE_URL in frontend config
3. Check browser console for CORS errors
4. Ensure backend CORS is configured to allow frontend origin

### Frontend not updating after changes

1. Rebuild the Docker image: `docker compose build --no-cache frontend`
2. Restart the container: `docker compose restart frontend`

### Port already in use

If port 3000 is already in use, change it in `docker-compose.yml`:

```yaml
ports:
  - "3001:80"  # Use port 3001 instead
```

## Accessing the Application

Once all services are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/docs




