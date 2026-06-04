#!/bin/bash
# ============================================================
# Smart Garden Dashboard — Entrypoint
# ============================================================
# Starts the Flask dashboard with Gunicorn in production mode.
# Override behavior with environment variables:
#   FLASK_PORT=5000       — port to listen on
#   FLASK_WORKERS=2       — Gunicorn worker count
#   DATABASE_URL=...      — PostgreSQL connection string
# ============================================================

set -e

echo "[smartgarden] Python: $(/opt/venv/bin/python --version 2>&1 || echo 'NOT FOUND')"
echo "[smartgarden] Starting Smart Garden Dashboard..."

# Ensure directories exist (volume mounts override Dockerfile mkdir)
mkdir -p logs data captures 2>/dev/null || true

# Initialize database tables (creates them if they don't exist)
echo "[smartgarden] Initializing database..."
/opt/venv/bin/python -c "
import sys
sys.path.insert(0, '/app')
from backend.main import app, db

with app.app_context():
    db.create_all()
    print('[smartgarden] Database tables ready')
"

PORT="${FLASK_PORT:-5000}"
WORKERS="${FLASK_WORKERS:-2}"

echo "[smartgarden] Listening on port ${PORT} with ${WORKERS} workers"

exec /opt/venv/bin/gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  "backend.main:app"
