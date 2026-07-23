# syntax=docker/dockerfile:1

# -------- Frontend (React → static) --------
FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin API when FastAPI serves the UI
ENV VITE_API_URL=
RUN npm run build

# -------- Backend runtime (FastAPI + AI + static UI) --------
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    ORT_DISABLE_MEMORY_ARENA=1 \
    MALLOC_ARENA_MAX=2 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# CPU wheels work on Oracle Ampere (arm64) and x86_64 Always Free shapes
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY backend/app ./app
RUN mkdir -p uploads outputs weights static

COPY --from=frontend /web/dist ./static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Single worker — AI models are memory-heavy on Always Free VMs
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "75"]
