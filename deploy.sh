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
  ssh "$DEPLOY_SSH_HOST" "mkdir -p '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures' 2>/dev/null || sudo mkdir -p '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures'"
  ssh "$DEPLOY_SSH_HOST" "sudo chown -R 1001:1001 '${DEPLOY_COMPOSE_DIR}/logs' '${DEPLOY_COMPOSE_DIR}/data' '${DEPLOY_COMPOSE_DIR}/captures'"
  ok "Remote directories ready"
}

source "${SCRIPT_DIR}/../deploy-kit/lib.sh"
