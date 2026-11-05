#!/usr/bin/env bash
# ==============================================================================
# Gadispot Developer Local Stack Startup Script (POSIX / Linux / macOS)
# Automates environment initialization, container build/start, readiness polling,
# and Alembic database migration execution.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "======================================================================"
echo "          Starting Gadispot Local Engineering Environment             "
echo "======================================================================"

# 1. Initialize environment configuration if absent
if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "[+] Initializing .env configuration from .env.example..."
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    echo "[✓] .env initialized successfully."
else
    echo "[i] Using existing .env configuration."
fi

# 2. Build and launch Docker Compose services
echo "[+] Building and launching Docker Compose services in background..."
docker compose up -d --build

# 3. Wait for database and backend services to report healthy
echo "[+] Waiting for services to attain HEALTHY state..."
MAX_ATTEMPTS=30
ATTEMPT=0
BACKEND_HEALTHY=false

while [ "${ATTEMPT}" -lt "${MAX_ATTEMPTS}" ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    # Check if backend container reports healthy or HTTP 200 on /health/ready
    if curl -s -f -o /dev/null "http://localhost:8000/health/ready" 2>/dev/null; then
        BACKEND_HEALTHY=true
        break
    fi
    
    echo "    Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Backend readiness pending, retrying in 2s..."
    sleep 2
done

if [ "${BACKEND_HEALTHY}" != true ]; then
    echo "[!] Timed out waiting for backend service readiness. Checking container logs:"
    docker compose logs --tail 30 backend
    exit 1
fi
echo "[✓] Backend and dependent datastores (PostgreSQL + Redis) are HEALTHY."

# 4. Apply database migrations via Alembic inside backend container
echo "[+] Applying latest database migrations (alembic upgrade head)..."
docker compose exec -T backend alembic upgrade head
echo "[✓] Database schema is up to date."

# 5. Output Success Banner
echo ""
echo "======================================================================"
echo "         🚀 Gadispot Local Development Environment Ready!             "
echo "======================================================================"
echo "  • Liveness Probe:     http://localhost:8000/health/live"
echo "  • Readiness Probe:    http://localhost:8000/health/ready"
echo "  • API Health Check:   http://localhost:8000/api/v1/health"
echo "  • Interactive Docs:   http://localhost:8000/docs"
echo "  • ReDoc Spec:         http://localhost:8000/redoc"
echo "  • PostgreSQL (PostGIS): localhost:5432 (DB: gadispot, User: postgres)"
echo "  • Redis Cache:        localhost:6379"
echo "======================================================================"
echo "To shut down the stack gracefully, run: ./scripts/dev_down.sh"
echo "To shut down and wipe persistent volumes: ./scripts/dev_down.sh -v"
echo "======================================================================"
