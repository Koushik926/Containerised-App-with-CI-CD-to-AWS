#!/bin/bash
set -euo pipefail

VM_NAME="ec2-sim"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if ! command -v multipass &> /dev/null; then
    log "Multipass is not installed"
    exit 0
fi

if ! multipass list | grep -q "^${VM_NAME}"; then
    log "VM '${VM_NAME}' does not exist"
    exit 0
fi

log "Stopping VM '${VM_NAME}'..."
multipass stop "$VM_NAME" 2>/dev/null || true

log "Deleting VM '${VM_NAME}'..."
multipass delete "$VM_NAME"

log "Purging deleted VMs..."
multipass purge

echo ""
echo "========================================"
echo "    EC2 SIMULATION VM DESTROYED"
echo "========================================"
echo ""
log "VM '${VM_NAME}' has been completely removed"
