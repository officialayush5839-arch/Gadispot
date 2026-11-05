#!/usr/bin/env bash
# ==============================================================================
# Gadispot Developer Local Stack Teardown Script (POSIX / Linux / macOS)
# Gracefully stops Docker Compose containers with optional persistent volume purge.
# Usage:
#   ./scripts/dev_down.sh           # Stop containers gracefully
#   ./scripts/dev_down.sh -v        # Stop containers and wipe volumes
#   ./scripts/dev_down.sh --volumes # Stop containers and wipe volumes
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

WIPE_VOLUMES=false

for arg in "$@"; do
    case "${arg}" in
        -v|--volumes)
            WIPE_VOLUMES=true
            ;;
        -h|--help)
            echo "Usage: $0 [-v|--volumes]"
            echo "  -v, --volumes   Wipe persistent named volumes (gadispot_pgdata, gadispot_redisdata)"
            exit 0
            ;;
    esac
done

echo "======================================================================"
echo "          Stopping Gadispot Local Engineering Environment             "
echo "======================================================================"

if [ "${WIPE_VOLUMES}" = true ]; then
    echo "[!] Stopping containers and PURGING persistent volumes..."
    docker compose down -v --remove-orphans
    echo "[✓] Containers stopped and volumes wiped successfully."
else
    echo "[+] Stopping containers gracefully (preserving data volumes)..."
    docker compose down --remove-orphans
    echo "[✓] Containers stopped. (Data volumes preserved; pass -v to wipe)."
fi
echo "======================================================================"
