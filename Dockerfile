# ============================================================
# Smart Garden Dashboard — Docker Build
# ============================================================
# Python/Flask backend serving the dashboard UI + REST API.
# Connects to PostgreSQL on the NAS for persistent storage.
#
# Build:
#   cd sun/SmartGardenDashBoard
#   docker build -t smartgarden-dashboard .
# ============================================================

FROM python:3.11-slim AS deps

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Production runner ─────────────────────────────────────────
FROM python:3.11-slim AS runner
WORKDIR /app

# Install wget for healthcheck + fonts for QR label generation + SSH for Pi camera
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       wget fonts-dejavu-core openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 1001 appgrp \
    && useradd --system --uid 1001 --gid appgrp -m -d /home/appusr appusr

# Create data directories
RUN mkdir -p /app/logs /app/data /app/captures \
    && chown -R appusr:appgrp /app/logs /app/data /app/captures

# ── Copy Python venv ──────────────────────────────────────────
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ── Copy backend source ──────────────────────────────────────
COPY backend/ ./backend/

# ── Pre-download YOLOv8-nano model ───────────────────────────
# Downloads at build time so the container works offline.
RUN mkdir -p ./backend/models \
    && python -c "from ultralytics import YOLO; m = YOLO('yolov8n.pt'); m.export(format='onnx', imgsz=640)" \
    && mv yolov8n.onnx ./backend/models/yolov8n.onnx \
    && rm -f yolov8n.pt || echo 'YOLO model pre-download skipped (will download at first run)'

# ── Copy frontend source ─────────────────────────────────────
COPY frontend/ ./frontend/

# ── Copy entrypoint ──────────────────────────────────────────
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

RUN chown -R appusr:appgrp /app

ENV PYTHONPATH="/app"

USER appusr

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:5000/api/dashboard/stats || exit 1

CMD ["./entrypoint.sh"]
