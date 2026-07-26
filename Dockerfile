# syntax=docker/dockerfile:1
# Railway / Render free deploy — CPU-only torch, tiny rembg model by default

FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=
RUN npm run build

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    ORT_DISABLE_MEMORY_ARENA=1 \
    MALLOC_ARENA_MAX=2 \
    TOKENIZERS_PARALLELISM=false \
    BG_PROVIDER=local \
    BIREFNET_MODEL=u2netp \
    BIREFNET_MAX_SIDE=640 \
    BIREFNET_PAD=20 \
    SAFE_INPUT_SIDE=1200 \
    MAX_PROCESS_SIDE=900 \
    MAX_OUTPUT_SIDE=2400 \
    REALESRGAN_TILE=64 \
    REALESRGAN_FAST_4X=true \
    REALESRGAN_2X_MAX_INPUT=640 \
    REALESRGAN_4X_MAX_INPUT=480 \
    PERFORMANCE_PROFILE=low \
    DEVICE=cpu \
    USE_TORCH_REALESRGAN=false \
    USE_GFPGAN_MODEL=false \
    UNLOAD_MODELS_AFTER_USE=true \
    CORS_ORIGINS=* \
    MAX_FILE_SIZE_MB=10

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# Force CPU PyTorch — default pip CUDA wheels OOMed free Railway
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY backend/app ./app
RUN mkdir -p uploads outputs weights static

COPY --from=frontend /web/dist ./static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=5 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75"]
