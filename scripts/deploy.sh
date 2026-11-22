#!/bin/bash
set -euo pipefail

IMAGE_TAG="${1:-latest}"
REGISTRY="ghcr.io"
IMAGE_NAME="koushik926/taskflow-api"
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_TAG=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

cd /opt/taskflow || error "Failed to cd to /opt/taskflow"

log "Starting deployment of ${IMAGE_NAME}:${IMAGE_TAG}"

if docker compose -f "$COMPOSE_FILE" ps --quiet app 2>/dev/null | grep -q .; then
    BACKUP_TAG=$(docker inspect --format='{{.Config.Image}}' taskflow-app 2>/dev/null | cut -d: -f2 || echo "")
    if [ -n "$BACKUP_TAG" ]; then
        log "Current running version: ${BACKUP_TAG}"
        echo "$BACKUP_TAG" > .last-deployed-tag
    fi
fi

log "Pulling image ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
docker pull "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" || error "Failed to pull image"

log "Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --timeout 30 || true

log "Starting new containers..."
IMAGE_TAG="$IMAGE_TAG" docker compose -f "$COMPOSE_FILE" up -d || error "Failed to start containers"

log "Waiting for health check..."
RETRIES=30
DELAY=2
for i in $(seq 1 $RETRIES); do
    if docker compose -f "$COMPOSE_FILE" ps app --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
        log "Application is healthy!"
        break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
        log "Health check failed after ${RETRIES} attempts"
        if [ -n "$BACKUP_TAG" ]; then
            log "Rolling back to previous version: ${BACKUP_TAG}"
            IMAGE_TAG="$BACKUP_TAG" docker compose -f "$COMPOSE_FILE" up -d
        fi
        error "Deployment failed - health check timeout"
    fi
    log "Waiting for app to become healthy (attempt $i/$RETRIES)..."
    sleep $DELAY
done

log "Cleaning up old images..."
docker image prune -f --filter "until=24h" || true

log "Deployment complete!"
docker compose -f "$COMPOSE_FILE" ps
