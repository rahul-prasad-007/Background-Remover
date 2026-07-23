# Hugging Face Spaces (Docker) — Shankar Card AI Image Enhancer
# Listens on PORT (default 7860). Serves React UI + FastAPI API.

# -------- Frontend build --------
FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=
RUN npm run build

# -------- Backend runtime (CPU) --------
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    ORT_DISABLE_MEMORY_ARENA=1 \
    HOME=/app \
    U2NET_HOME=/app/.u2net \
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch \
    PORT=7860 \
    BG_PROVIDER=local \
    BIREFNET_MODEL=birefnet-general-lite \
    BIREFNET_MAX_SIDE=640 \
    BIREFNET_PAD=24 \
    PERFORMANCE_PROFILE=low \
    SAFE_INPUT_SIDE=1280 \
    REALESRGAN_TILE=96 \
    REALESRGAN_THREADS=2 \
    REALESRGAN_FAST_4X=true \
    REALESRGAN_2X_MAX_INPUT=800 \
    REALESRGAN_4X_MAX_INPUT=560 \
    MAX_PROCESS_SIDE=900 \
    MAX_OUTPUT_SIDE=2400 \
    USE_TORCH_REALESRGAN=true \
    USE_GFPGAN_MODEL=false \
    UNLOAD_MODELS_AFTER_USE=true \
    MAX_FILE_SIZE_MB=12 \
    CORS_ORIGINS=* \
    DEVICE=cpu

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch (smaller image — better for free Spaces)
RUN pip install --upgrade pip \
    && pip install torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements-spaces.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY backend/uploads ./uploads
COPY backend/outputs ./outputs
COPY backend/weights ./weights
COPY --from=frontend /web/dist ./static
COPY start.sh ./start.sh

RUN sed -i 's/\r$//' /app/start.sh \
    && chmod +x /app/start.sh \
    && mkdir -p /app/.u2net /app/.cache/huggingface /app/.cache/torch \
               /app/uploads /app/outputs /app/weights \
    && useradd -m -u 1000 user \
    && chown -R user:user /app

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=5 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-7860}/api/health" || exit 1

CMD ["/app/start.sh"]
