#!/bin/bash
set -euo pipefail

REGISTRY="ghcr.io"
IMAGE_NAME="koushik926/taskflow-api"
COMPOSE_FILE="docker-compose.prod.yml"
DEPLOY_DIR="/opt/taskflow"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

cd "$DEPLOY_DIR" || error "Failed to cd to $DEPLOY_DIR"

if [ -f .env ]; then
    log "Loading environment from .env"
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

TARGET_TAG="${1:-}"

if [ -z "$TARGET_TAG" ]; then
    if [ -f .previous_tag ]; then
        TARGET_TAG=$(cat .previous_tag)
        log "No tag specified, using previous: ${TARGET_TAG}"
    else
        error "No tag specified and no .previous_tag file found. Usage: $0 <image_tag>"
    fi
fi

CURRENT_TAG=""
if [ -f .current_tag ]; then
    CURRENT_TAG=$(cat .current_tag)
fi

if [ "$TARGET_TAG" = "$CURRENT_TAG" ]; then
    log "Target tag ${TARGET_TAG} is already the current version"
    exit 0
fi

echo ""
echo "========================================"
echo "       MANUAL ROLLBACK STARTING"
echo "========================================"
echo "  From: ${CURRENT_TAG:-unknown}"
echo "  To:   ${TARGET_TAG}"
echo "========================================"
echo ""

log "Pulling image ${REGISTRY}/${IMAGE_NAME}:${TARGET_TAG}"
docker pull "${REGISTRY}/${IMAGE_NAME}:${TARGET_TAG}" || error "Failed to pull image"

log "Stopping current containers..."
docker compose -f "$COMPOSE_FILE" down --timeout 30 || true

log "Starting containers with tag: ${TARGET_TAG}"
export IMAGE_TAG="$TARGET_TAG"
docker compose -f "$COMPOSE_FILE" up -d || error "Failed to start containers"

log "Waiting for health check..."
RETRIES=30
DELAY=2
HEALTHY=false

for i in $(seq 1 $RETRIES); do
    if docker compose -f "$COMPOSE_FILE" ps app --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
        log "Application is healthy!"
        HEALTHY=true
        break
    fi
    log "Waiting for app to become healthy (attempt $i/$RETRIES)..."
    sleep $DELAY
done

if [ "$HEALTHY" = false ]; then
    error "Rollback failed - health check timeout. Manual intervention required."
fi

if [ -n "$CURRENT_TAG" ]; then
    echo "$CURRENT_TAG" > .previous_tag
fi
echo "$TARGET_TAG" > .current_tag

echo ""
echo "========================================"
echo "       ROLLBACK SUCCESSFUL"
echo "========================================"
echo "  Now running: ${TARGET_TAG}"
echo "========================================"
echo ""

docker compose -f "$COMPOSE_FILE" ps
