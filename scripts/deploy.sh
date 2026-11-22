#!/bin/bash
set -euo pipefail

IMAGE_TAG="${1:-latest}"
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

rollback() {
    local previous_tag="$1"
    echo ""
    echo "========================================"
    echo "        ROLLBACK IN PROGRESS"
    echo "========================================"
    log "ROLLBACK: Reverting to previous version: ${previous_tag}"

    IMAGE_TAG="$previous_tag" docker compose -f "$COMPOSE_FILE" up -d

    log "ROLLBACK: Waiting for rollback to stabilize..."
    sleep 10

    if docker compose -f "$COMPOSE_FILE" ps app --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
        log "ROLLBACK: Previous version is healthy and serving traffic"
    else
        log "ROLLBACK: Warning - previous version health status unknown"
    fi

    echo "========================================"
    echo "  ROLLBACK COMPLETE - OLD VERSION LIVE"
    echo "========================================"
    echo ""
}

cd "$DEPLOY_DIR" || error "Failed to cd to $DEPLOY_DIR"

if [ -f .env ]; then
    log "Loading environment from .env"
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

log "Starting deployment of ${IMAGE_NAME}:${IMAGE_TAG}"

PREVIOUS_TAG=""
if [ -f .current_tag ]; then
    PREVIOUS_TAG=$(cat .current_tag)
    log "Previous deployed version: ${PREVIOUS_TAG}"
fi

if docker compose -f "$COMPOSE_FILE" ps --quiet app 2>/dev/null | grep -q .; then
    RUNNING_TAG=$(docker inspect --format='{{.Config.Image}}' taskflow-app 2>/dev/null | cut -d: -f2 || echo "")
    if [ -n "$RUNNING_TAG" ] && [ "$RUNNING_TAG" != "$PREVIOUS_TAG" ]; then
        PREVIOUS_TAG="$RUNNING_TAG"
        log "Updated previous version from running container: ${PREVIOUS_TAG}"
    fi
fi

if [ -n "$PREVIOUS_TAG" ]; then
    echo "$PREVIOUS_TAG" > .previous_tag
    log "Saved previous tag to .previous_tag"
fi

log "Pulling image ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
docker pull "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" || error "Failed to pull image"

log "Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --timeout 30 || true

log "Starting new containers with tag: ${IMAGE_TAG}"
export IMAGE_TAG
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
    log "Health check failed after ${RETRIES} attempts ($(( RETRIES * DELAY )) seconds)"

    if [ -n "$PREVIOUS_TAG" ]; then
        rollback "$PREVIOUS_TAG"
        error "Deployment failed - automatic rollback performed"
    else
        error "Deployment failed - no previous version to rollback to"
    fi
fi

echo "$IMAGE_TAG" > .current_tag
log "Saved current tag to .current_tag"

log "Cleaning up old images (keeping last 3 versions)..."
IMAGES_TO_KEEP=$(docker images "${REGISTRY}/${IMAGE_NAME}" --format "{{.ID}}" | head -3 | tr '\n' '|' | sed 's/|$//')
if [ -n "$IMAGES_TO_KEEP" ]; then
    docker images "${REGISTRY}/${IMAGE_NAME}" --format "{{.ID}} {{.Tag}}" | \
        tail -n +4 | \
        awk '{print $1}' | \
        xargs -r docker rmi 2>/dev/null || true
fi
docker image prune -f || true

log "Deployment complete!"
echo ""
echo "========================================"
echo "       DEPLOYMENT SUCCESSFUL"
echo "========================================"
echo "  Image: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "========================================"
echo ""
docker compose -f "$COMPOSE_FILE" ps
