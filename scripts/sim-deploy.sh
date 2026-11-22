#!/bin/bash
set -euo pipefail

VM_NAME="ec2-sim"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REGISTRY="ghcr.io"
IMAGE_NAME="koushik926/taskflow-api"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

if ! command -v multipass &> /dev/null; then
    error "Multipass is not installed"
fi

if ! multipass list | grep -q "^${VM_NAME}.*Running"; then
    error "VM '${VM_NAME}' is not running. Run 'make sim-up' first."
fi

VM_IP=$(multipass info "$VM_NAME" --format json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['$VM_NAME']['ipv4'][0])")
log "Deploying to VM at ${VM_IP}"

IMAGE_TAG="${1:-}"
if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    log "No tag specified, using: ${IMAGE_TAG}"
fi

LOCAL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${LOCAL_IMAGE}$"; then
    log "Found local image: ${LOCAL_IMAGE}"
    USE_LOCAL=true
else
    log "Local image not found, will pull from registry"
    USE_LOCAL=false
fi

log "Copying deployment files to VM..."
multipass transfer "$PROJECT_DIR/docker-compose.prod.yml" "${VM_NAME}:/opt/taskflow/"
multipass transfer "$PROJECT_DIR/scripts/deploy.sh" "${VM_NAME}:/opt/taskflow/"
multipass transfer "$PROJECT_DIR/scripts/rollback.sh" "${VM_NAME}:/opt/taskflow/"
multipass exec "$VM_NAME" -- sudo mkdir -p /opt/taskflow/nginx/conf.d
multipass transfer "$PROJECT_DIR/nginx/nginx.conf" "${VM_NAME}:/tmp/nginx.conf"
multipass transfer "$PROJECT_DIR/nginx/conf.d/default.conf" "${VM_NAME}:/tmp/default.conf"
multipass exec "$VM_NAME" -- sudo mv /tmp/nginx.conf /opt/taskflow/nginx/
multipass exec "$VM_NAME" -- sudo mv /tmp/default.conf /opt/taskflow/nginx/conf.d/
multipass exec "$VM_NAME" -- sudo chown -R deploy:deploy /opt/taskflow

if [ "$USE_LOCAL" = true ]; then
    log "Saving and transferring local image to VM..."
    TEMP_TAR="/tmp/${IMAGE_TAG}.tar"
    docker save "$LOCAL_IMAGE" -o "$TEMP_TAR"
    multipass transfer "$TEMP_TAR" "${VM_NAME}:/tmp/"
    multipass exec "$VM_NAME" -- sudo docker load -i "/tmp/${IMAGE_TAG}.tar"
    rm -f "$TEMP_TAR"
    multipass exec "$VM_NAME" -- rm -f "/tmp/${IMAGE_TAG}.tar"
fi

log "Creating .env file on VM..."
multipass exec "$VM_NAME" -- bash -c "cat > /opt/taskflow/.env << 'ENV'
SECRET_KEY=sim-local-secret-key-for-testing
DATABASE_URL=postgresql+asyncpg://taskflow:taskflow@db:5432/taskflow
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS_STR=http://localhost,http://${VM_IP}
ENV"

log "Running deploy.sh on VM..."
multipass exec "$VM_NAME" -- bash -c "cd /opt/taskflow && chmod +x deploy.sh rollback.sh && ./deploy.sh ${IMAGE_TAG}"

log "Waiting for services to start..."
sleep 5

log "Checking deployment status..."
for i in {1..12}; do
    if curl -sf "http://${VM_IP}/health/ready" > /dev/null 2>&1; then
        log "Health check passed!"
        break
    fi
    if [ "$i" -eq 12 ]; then
        log "Warning: Health check not responding yet"
    fi
    log "Waiting for health check (attempt $i/12)..."
    sleep 5
done

echo ""
echo "========================================"
echo "    SIMULATION DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "  App URL:    http://${VM_IP}"
echo "  API Docs:   http://${VM_IP}/docs"
echo "  Health:     http://${VM_IP}/health/ready"
echo "  Version:    http://${VM_IP}/version"
echo ""

VERSION_INFO=$(curl -sf "http://${VM_IP}/version" 2>/dev/null || echo '{"error": "not ready"}')
echo "  Version Info:"
echo "$VERSION_INFO" | python3 -m json.tool 2>/dev/null || echo "$VERSION_INFO"
echo ""
echo "  Test commands:"
echo "    curl http://${VM_IP}/health/ready"
echo "    curl http://${VM_IP}/version"
echo ""
echo "  To rollback:"
echo "    multipass exec ${VM_NAME} -- /opt/taskflow/rollback.sh <tag>"
echo ""
echo "========================================"
