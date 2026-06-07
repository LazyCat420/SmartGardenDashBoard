#!/bin/bash
# ============================================================
# Smart Garden Dashboard — Build & Deploy to Synology NAS
#
# Thin wrapper — all logic lives in ../deploy-kit/lib.sh
#
# Usage:
#   npm run deploy              # full deploy
#   npm run deploy -- --dry-run # validate without deploying
#   npm run deploy -- --skip-pull
#   npm run deploy -- --no-cache
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="smartgarden-dashboard"
DISPLAY_NAME="🌱 Smart Garden Dashboard"
SKIP_ENV_DEPLOY=true

PRE_BUILD() {
  local CENTRAL_ENV="${DEPLOY_KIT_DIR}/.env.deploy"
  if [ -f "$CENTRAL_ENV" ]; then
    set -a; source "$CENTRAL_ENV"; set +a
    info "Loaded deploy-kit/.env.deploy"
  fi
}

EXTRA_SSH_SYNC() {
  info "Creating data directories on remote host..."
  ssh "$DEPLOY_SSH_HOST" "mkdir -p '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures' '${DEPLOY_COMPOSE_DIR}/ssh_keys' 2>/dev/null || sudo mkdir -p '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures' '${DEPLOY_COMPOSE_DIR}/ssh_keys'"
  
  info "Copying SSH keys and config to remote host via pipe..."
  cat "${SCRIPT_DIR}/ssh_keys/id_ed25519" | ssh "$DEPLOY_SSH_HOST" "sudo tee '${DEPLOY_COMPOSE_DIR}/ssh_keys/id_ed25519' >/dev/null"
  cat "${SCRIPT_DIR}/ssh_keys/id_ed25519.pub" | ssh "$DEPLOY_SSH_HOST" "sudo tee '${DEPLOY_COMPOSE_DIR}/ssh_keys/id_ed25519.pub' >/dev/null"
  if [ -f "${SCRIPT_DIR}/ssh_keys/config" ]; then
    cat "${SCRIPT_DIR}/ssh_keys/config" | ssh "$DEPLOY_SSH_HOST" "sudo tee '${DEPLOY_COMPOSE_DIR}/ssh_keys/config' >/dev/null"
  fi
  
  info "Setting correct permissions on remote host..."
  ssh "$DEPLOY_SSH_HOST" "sudo chown -R 1001:1001 '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures' '${DEPLOY_COMPOSE_DIR}/ssh_keys' && sudo chmod 700 '${DEPLOY_COMPOSE_DIR}/ssh_keys' && sudo chmod 600 '${DEPLOY_COMPOSE_DIR}/ssh_keys/id_ed25519' && ( [ ! -f '${DEPLOY_COMPOSE_DIR}/ssh_keys/config' ] || sudo chmod 644 '${DEPLOY_COMPOSE_DIR}/ssh_keys/config' )"
  ok "Remote directories and SSH keys ready"
}

source "${SCRIPT_DIR}/../deploy-kit/lib.sh"
