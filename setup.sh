#!/usr/bin/env bash
# RAGDocs Setup Script
# Usage:
#   ./setup.sh           — full local dev setup (venv + frontend + docker infra)
#   ./setup.sh --docker  — build and start everything via Docker Compose
#   ./setup.sh --backend — backend only (venv + pip)
#   ./setup.sh --frontend — frontend only (npm install)

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Parse args ────────────────────────────────────────────────────────────────
MODE="full"
for arg in "$@"; do
  case $arg in
    --docker)   MODE="docker"   ;;
    --backend)  MODE="backend"  ;;
    --frontend) MODE="frontend" ;;
    --help|-h)
      echo "Usage: ./setup.sh [--docker | --backend | --frontend]"
      echo "  (no flag)    Full local dev: venv + pip + npm + start Docker infra"
      echo "  --docker     Build & start everything with Docker Compose"
      echo "  --backend    Python venv + pip install only"
      echo "  --frontend   npm install only"
      exit 0 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ██████╗  █████╗  ██████╗ ██████╗  ██████╗  ██████╗███████╗"
echo "  ██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔═══██╗██╔════╝██╔════╝"
echo "  ██████╔╝███████║██║  ███╗██║  ██║██║   ██║██║     ███████╗"
echo "  ██╔══██╗██╔══██║██║   ██║██║  ██║██║   ██║██║     ╚════██║"
echo "  ██║  ██║██║  ██║╚██████╔╝██████╔╝╚██████╔╝╚██████╗███████║"
echo "  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝╚══════╝"
echo ""
info "Mode: $MODE"
echo ""

# ── Check prerequisites ────────────────────────────────────────────────────────
check_cmd() {
  command -v "$1" &>/dev/null || error "'$1' not found. Please install it first."
}

if [[ "$MODE" == "docker" ]]; then
  check_cmd docker
  docker info &>/dev/null || error "Docker daemon is not running."
  check_cmd docker compose 2>/dev/null || check_cmd docker-compose 2>/dev/null || error "docker compose not found."
else
  if [[ "$MODE" != "frontend" ]]; then
    check_cmd python3
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    [[ "$(echo "$PY_VERSION >= 3.11" | bc)" == "1" ]] 2>/dev/null || \
      python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" || \
      error "Python 3.10+ required (found $PY_VERSION)"
    success "Python $PY_VERSION"
  fi
  if [[ "$MODE" != "backend" ]]; then
    check_cmd node
    check_cmd npm
    NODE_VER=$(node --version)
    success "Node $NODE_VER"
  fi
fi

# ── .env setup ────────────────────────────────────────────────────────────────
setup_env() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      warn ".env created from .env.example — set GEMINI_API_KEY before starting"
    else
      cat > .env << 'EOF'
# Required: Google Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional overrides
# GEMINI_MODEL=gemini-2.5-flash
# CORS_ORIGINS=http://localhost:3001,https://your-domain.com
EOF
      warn ".env created — set GEMINI_API_KEY before starting"
    fi
  else
    success ".env already exists"
  fi

  # Warn if key is still placeholder
  if grep -q "your_gemini_api_key_here" .env 2>/dev/null; then
    warn "GEMINI_API_KEY is not set in .env — LLM features won't work"
  fi
}

# ── Backend setup ─────────────────────────────────────────────────────────────
setup_backend() {
  info "Setting up Python virtual environment..."
  VENV_DIR="$SCRIPT_DIR/.venv"

  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    success "Created .venv"
  else
    success ".venv already exists"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  info "Upgrading pip..."
  pip install --quiet --upgrade pip

  info "Installing Python packages (this may take a few minutes for torch/transformers)..."
  pip install --quiet -r requirements.txt
  success "Python packages installed"

  # Pre-download embedding models so first startup is fast
  info "Pre-downloading embedding models (all-MiniLM-L6-v2 + jina-code)..."
  python3 - << 'PYEOF'
import sys
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    print("  Downloading all-MiniLM-L6-v2...", flush=True)
    SentenceTransformer('all-MiniLM-L6-v2')
    print("  Downloading BAAI/bge-reranker-base...", flush=True)
    CrossEncoder('BAAI/bge-reranker-base')
    # Jina code model is large (~500MB) — skip if CI/low-disk
    import os
    if os.getenv('SKIP_JINA') != '1':
        print("  Downloading jinaai/jina-embeddings-v2-base-code (~500MB)...", flush=True)
        SentenceTransformer('jinaai/jina-embeddings-v2-base-code', trust_remote_code=True)
    print("  Models ready.")
except Exception as e:
    print(f"  Warning: model pre-download failed ({e}) — will download on first startup")
    sys.exit(0)
PYEOF
  success "Embedding models cached"

  mkdir -p uploads
  success "uploads/ directory ready"
}

# ── Frontend setup ────────────────────────────────────────────────────────────
setup_frontend() {
  info "Installing frontend npm packages..."
  cd "$SCRIPT_DIR/frontend"
  npm install --silent
  success "npm packages installed"
  cd "$SCRIPT_DIR"
}

# ── Docker infra (Postgres + Qdrant only, no app containers) ──────────────────
start_infra() {
  check_cmd docker
  docker info &>/dev/null || { warn "Docker not running — skipping infra startup"; return; }

  info "Starting Postgres + Qdrant via Docker..."
  COMPOSE_PROFILES="" docker compose up -d postgres qdrant 2>/dev/null || \
    docker compose up -d postgres qdrant

  info "Waiting for Postgres to be healthy..."
  for i in $(seq 1 20); do
    if docker compose exec -T postgres pg_isready -U ragdocs &>/dev/null 2>&1; then
      success "Postgres is ready"
      break
    fi
    [[ $i -eq 20 ]] && warn "Postgres not ready after 20s — check docker logs"
    sleep 1
  done

  success "Qdrant started (http://localhost:6333/dashboard)"
}

# ── Full Docker mode ──────────────────────────────────────────────────────────
run_docker() {
  setup_env
  info "Building and starting all services with Docker Compose..."
  docker compose up -d --build
  success "All services started"
  echo ""
  echo "  Frontend : http://localhost:3001"
  echo "  Backend  : http://localhost:8000"
  echo "  API docs : http://localhost:8000/docs"
  echo "  Qdrant   : http://localhost:6333/dashboard"
  echo ""
  echo "  Logs: docker compose logs -f"
  echo "  Stop: docker compose down"
}

# ── Print local dev start instructions ───────────────────────────────────────
print_start_instructions() {
  echo ""
  echo "  ════════════════════════════════════════════════════"
  echo "  Setup complete. To start the app:"
  echo ""
  echo "  Terminal 1 — Backend:"
  echo "    source .venv/bin/activate"
  echo "    uvicorn app.main:app --reload --port 8000"
  echo ""
  echo "  Terminal 2 — Frontend:"
  echo "    cd frontend && npm run dev"
  echo ""
  echo "  Services:"
  echo "    Frontend : http://localhost:3000"
  echo "    Backend  : http://localhost:8000"
  echo "    API docs : http://localhost:8000/docs"
  echo "    Qdrant   : http://localhost:6333/dashboard"
  echo "  ════════════════════════════════════════════════════"
  echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "$MODE" in
  docker)
    run_docker
    ;;
  backend)
    setup_env
    setup_backend
    print_start_instructions
    ;;
  frontend)
    setup_frontend
    ;;
  full)
    setup_env
    setup_backend
    setup_frontend
    start_infra
    print_start_instructions
    ;;
esac

success "Done."
