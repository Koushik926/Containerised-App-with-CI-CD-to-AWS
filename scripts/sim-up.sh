#!/bin/bash
set -euo pipefail

VM_NAME="ec2-sim"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
USER_DATA="$PROJECT_DIR/infra/terraform/user_data.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*" >&2
    exit 1
}

if ! command -v multipass &> /dev/null; then
    error "Multipass is not installed. Install it from https://multipass.run/"
fi

if multipass list | grep -q "^${VM_NAME}"; then
    log "VM '${VM_NAME}' already exists"
    log "Use 'make sim-down' to destroy it first, or 'make sim-deploy' to deploy"
    multipass info "$VM_NAME"
    exit 0
fi

if [ ! -f "$USER_DATA" ]; then
    error "user_data.sh not found at $USER_DATA"
fi

log "Creating Multipass VM '${VM_NAME}'..."
log "  - Ubuntu 24.04"
log "  - 1 CPU, 1GB RAM, 6GB disk"
log "  - Running user_data.sh via cloud-init"

CLOUD_INIT=$(mktemp)
cat > "$CLOUD_INIT" << 'CLOUDINIT'
#cloud-config
users:
  - default
  - name: deploy
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... placeholder

write_files:
  - path: /tmp/user_data.sh
    permissions: '0755'
    content: |
CLOUDINIT

sed 's/^/      /' "$USER_DATA" >> "$CLOUD_INIT"

cat >> "$CLOUD_INIT" << 'CLOUDINIT'

runcmd:
  - /tmp/user_data.sh
CLOUDINIT

multipass launch 24.04 \
    --name "$VM_NAME" \
    --cpus 1 \
    --memory 1G \
    --disk 6G \
    --cloud-init "$CLOUD_INIT"

rm -f "$CLOUD_INIT"

log "Waiting for VM to be ready..."
sleep 10

log "Setting up SSH access for 'deploy' user..."
multipass exec "$VM_NAME" -- sudo mkdir -p /home/deploy/.ssh
multipass exec "$VM_NAME" -- sudo cp /home/ubuntu/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
multipass exec "$VM_NAME" -- sudo chown -R deploy:deploy /home/deploy/.ssh 2>/dev/null || true

log "Waiting for cloud-init to complete..."
multipass exec "$VM_NAME" -- cloud-init status --wait || true

log "Verifying Docker installation..."
multipass exec "$VM_NAME" -- docker --version || log "Warning: Docker may still be installing"
multipass exec "$VM_NAME" -- docker compose version || true

VM_IP=$(multipass info "$VM_NAME" --format json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['$VM_NAME']['ipv4'][0])")

echo ""
echo "========================================"
echo "    EC2 SIMULATION VM READY"
echo "========================================"
echo "  VM Name: ${VM_NAME}"
echo "  IP:      ${VM_IP}"
echo ""
echo "  SSH:     multipass shell ${VM_NAME}"
echo "  Deploy:  make sim-deploy"
echo "  Destroy: make sim-down"
echo ""
echo "  Note: This is a local rehearsal only."
echo "  Real deployments target AWS EC2."
echo "========================================"
