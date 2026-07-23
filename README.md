# Shankar Card — AI Image Enhancer

Print-ready image pipeline for commercial card / press work:

**Background removal → Face restore (if needed) → Real-ESRGAN upscale → Catalog polish → Transparent PNG**

Progress streams from the backend via Server-Sent Events (real stages, not fake loaders).

## Project structure

```
├── frontend/                 # React + Vite UI
├── backend/                  # FastAPI AI pipeline
│   ├── app/
│   ├── .env.example          # Copy → .env for Docker / local
│   └── requirements.txt
├── deploy/
│   ├── nginx.conf            # Reverse proxy (port 80 → app)
│   └── nginx-ssl.conf.example
├── Dockerfile                # Builds UI + API image
├── docker-compose.yml        # app + nginx (restart unless-stopped)
├── .dockerignore
├── DEPLOY_ORACLE.md          # Oracle Always Free step-by-step
├── DEPLOY.md                 # Generic Docker / Render notes
└── README.md
```

## Quick start (Windows — development)

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

Open **http://localhost:5173** (Vite proxies `/api` → `:8000`).

## Production on Oracle Cloud Always Free

Full guide: **[DEPLOY_ORACLE.md](DEPLOY_ORACLE.md)**

After the Ubuntu VM + Docker are ready:

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
docker compose up -d --build
```

Open **http://YOUR_PUBLIC_IP/** (Nginx on port **80** → FastAPI serves React + `/api`).

Use an **Ampere A1** shape with **≥8 GB RAM** (1 GB Micro shapes will crash).

## Environment

Copy `backend/.env.example` → `backend/.env`.

| Variable | Purpose |
|---|---|
| `BG_PROVIDER=local` | Free unlimited BiRefNet (default) |
| `BG_PROVIDER=removebg` | Paid remove.bg API |
| `REMOVE_BG_API_KEY` | Required only for remove.bg |
| `SAFE_INPUT_SIDE` | Cap image size for low RAM |
| `CORS_ORIGINS` | `*` behind Nginx, or your https domain |
| `REALESRGAN_*` | Upscale tiles / quality |

Weights download automatically on first use into the Docker `app-weights` volume (or `backend/weights/` locally).

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/info` | Service info |
| `POST` | `/api/process` | Multipart `file` + `quality` → SSE progress |
| `GET` | `/api/download/{job_id}` | Download transparent PNG |

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Uvicorn, Pillow, OpenCV, rembg, PyTorch |
| AI | BiRefNet / remove.bg, YuNet, Real-ESRGAN, catalog edge polish |
| Deploy | Docker Compose + Nginx |

## License

Private — Shankar Card
