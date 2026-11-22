#!/bin/bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

cd /opt/taskflow || error "Failed to cd to /opt/taskflow"

TARGET_TAG="${1:-}"

if [ -z "$TARGET_TAG" ]; then
    if [ -f .last-deployed-tag ]; then
        TARGET_TAG=$(cat .last-deployed-tag)
        log "No tag specified, using last deployed: ${TARGET_TAG}"
    else
        error "No tag specified and no .last-deployed-tag file found"
    fi
fi

log "Rolling back to version: ${TARGET_TAG}"

log "Stopping current containers..."
docker compose -f "$COMPOSE_FILE" down --timeout 30 || true

log "Starting containers with tag: ${TARGET_TAG}"
IMAGE_TAG="$TARGET_TAG" docker compose -f "$COMPOSE_FILE" up -d || error "Failed to start containers"

log "Waiting for health check..."
RETRIES=30
DELAY=2
for i in $(seq 1 $RETRIES); do
    if docker compose -f "$COMPOSE_FILE" ps app --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
        log "Rollback successful - application is healthy!"
        break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
        error "Rollback failed - health check timeout"
    fi
    log "Waiting for app to become healthy (attempt $i/$RETRIES)..."
    sleep $DELAY
done

log "Rollback complete!"
docker compose -f "$COMPOSE_FILE" ps
