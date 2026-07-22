# Shankar Card — AI Image Enhancer

Print-ready image pipeline for commercial card / press work:

**Background removal → Face restore (if needed) → Real-ESRGAN upscale → Catalog polish → Transparent PNG**

Progress streams from the backend via Server-Sent Events (real stages, not fake loaders).

## Project structure

```
├── frontend/               # React + Vite UI
│   └── src/
│       ├── components/     # UI sections
│       └── services/       # API client
├── backend/                # FastAPI AI pipeline
│   ├── app/
│   │   ├── api/            # HTTP routes
│   │   ├── services/       # BG remove, ESRGAN, faces, polish
│   │   ├── utils/          # Image helpers
│   │   ├── schemas.py      # Progress / SSE models
│   │   ├── config.py
│   │   └── main.py
│   ├── uploads/            # Temp uploads (gitignored)
│   ├── outputs/            # Result PNGs (gitignored)
│   ├── weights/            # Model weights (auto-download)
│   ├── .env.example
│   └── requirements.txt
├── start-backend.bat
├── start-frontend.bat
└── package.json
```

## Quick start (Windows)

### 1. Backend

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or double-click `start-backend.bat` after the venv exists.

### 2. Frontend

```bat
cd frontend
npm install
npm run dev
```

Or double-click `start-frontend.bat`.

Open **http://localhost:5173**

## Environment

Copy `backend/.env.example` → `backend/.env`.

| Variable | Purpose |
|---|---|
| `BG_PROVIDER=local` | Free unlimited BiRefNet (default) |
| `BG_PROVIDER=removebg` | Paid remove.bg API |
| `REMOVE_BG_API_KEY` | Required only for remove.bg |
| `SAFE_INPUT_SIDE` | Cap image size for low RAM |
| `REALESRGAN_*` | Upscale tiles / quality |

Weights (YuNet, Real-ESRGAN) download automatically into `backend/weights/` on first use. BiRefNet models cache under `%USERPROFILE%\.u2net\`.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/process` | Multipart `file` + `quality` (`auto` \| `original` \| `2` \| `4`) → SSE progress |
| `GET` | `/api/download/{job_id}` | Download transparent PNG |

## Production build (frontend)

```bat
cd frontend
npm install
npm run build
```

Serve `frontend/dist/` behind Nginx/Caddy and proxy `/api` to the FastAPI process (Uvicorn/Gunicorn).

### Backend production example

```bat
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Use **1 worker** on 8GB RAM machines (models are memory-heavy). Prefer `quality=original` or `2` for clients on low-end PCs.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Uvicorn, Pillow, OpenCV, rembg, PyTorch |
| AI | BiRefNet / remove.bg, YuNet, Real-ESRGAN, catalog edge polish |

## License

Private — Shankar Card
