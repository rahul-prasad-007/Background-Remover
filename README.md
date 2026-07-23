---
title: Shankar Card AI Image Enhancer
emoji: 🖼️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: other
short_description: Print-ready background removal, face restore & HD upscale
---

# Shankar Card — AI Image Enhancer

Print-ready image pipeline for commercial card / press work:

**Background removal → Face restore (if needed) → Real-ESRGAN upscale → Catalog polish → Transparent PNG**

Progress streams from the backend via Server-Sent Events (real stages, not fake loaders).

> **Deploy on Hugging Face Spaces (free Docker):** see [Hugging Face Spaces deployment](#hugging-face-spaces-deployment-free) below.

## Project structure

```
├── Dockerfile                 # HF Spaces / Docker (port 7860)
├── start.sh                   # Container entrypoint
├── .dockerignore
├── frontend/                  # React + Vite UI
├── backend/                   # FastAPI AI pipeline
│   ├── app/
│   ├── requirements.txt       # Local development (includes torch)
│   ├── requirements-spaces.txt# Docker / Spaces (torch installed as CPU wheel)
│   └── .env.example
├── start-backend.bat
├── start-frontend.bat
└── package.json
```

## Hugging Face Spaces deployment (FREE)

### Exact clicks after your code is on GitHub

1. Open **[https://huggingface.co/new-space](https://huggingface.co/new-space)** (log in first).
2. **Space name:** e.g. `background-remover` (any name).
3. **License:** pick any (e.g. `other`).
4. **Select the Space SDK:** click **Docker**.
5. **Space hardware:** leave **CPU basic (FREE)** for free tier  
   (upgrade later if you hit out-of-memory).
6. Click **Create Space**.
7. On the new Space page, open the **Settings** tab.
8. Scroll to **Repository / Linked GitHub repository** (wording may be **“Factory reboot”** section nearby):
   - Click **Connect repository** / **Link a GitHub account** if needed.
   - Authorize Hugging Face to access GitHub.
   - Choose repo: **`rahul-prasad-007/Background-Remover`**.
   - Branch: **`main`**.
9. Save / confirm. Hugging Face will **build the Dockerfile** automatically.
10. Wait for the build logs (first build can take **15–40 minutes** — Node build + PyTorch CPU install).
11. When status is **Running**, open the Space URL:  
    `https://huggingface.co/spaces/<your-username>/<space-name>`

### Optional Space Variables (Settings → Variables and secrets)

You usually need **none**. Defaults are already free-tier friendly.

| Variable | Default | When to set |
|---|---|---|
| `BG_PROVIDER` | `local` | Keep `local` on free Spaces |
| `REMOVE_BG_API_KEY` | _(empty)_ | Only if `BG_PROVIDER=removebg` |
| `SAFE_INPUT_SIDE` | `1280` | Lower to `1024` if OOM |
| `BIREFNET_MAX_SIDE` | `640` | Lower to `512` if OOM |
| `PORT` | `7860` | Do not change on Spaces |

### First-run note

The **first image** you process may take longer while BiRefNet / Real-ESRGAN weights download into the container. Later runs are faster.

### If the Space crashes (OOM)

In Space **Settings → Variables**, set:

```
SAFE_INPUT_SIDE=1024
BIREFNET_MAX_SIDE=512
REALESRGAN_2X_MAX_INPUT=640
MAX_FILE_SIZE_MB=8
```

Then **Factory reboot** the Space. Prefer UI quality **Original** or **2×** (avoid **4×** on free CPU).

---

## Local development (Windows)

### Backend

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bat
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Environment (local)

Copy `backend/.env.example` → `backend/.env`.

| Variable | Purpose |
|---|---|
| `BG_PROVIDER=local` | Free unlimited BiRefNet (default) |
| `BG_PROVIDER=removebg` | Paid remove.bg API |
| `REMOVE_BG_API_KEY` | Required only for remove.bg |
| `SAFE_INPUT_SIDE` | Cap image size for low RAM |

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/process` | Multipart `file` + `quality` → SSE progress |
| `GET` | `/api/download/{job_id}` | Download transparent PNG |

## Other deploy options

See **[DEPLOY.md](DEPLOY.md)** for Docker Compose / VPS / Render.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Uvicorn, Pillow, OpenCV, rembg, PyTorch (CPU on Spaces) |
| AI | BiRefNet, YuNet, Real-ESRGAN, catalog edge polish |

## License

Private — Shankar Card
