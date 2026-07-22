# Deploy guide — Shankar Card AI Image Enhancer

Repo: https://github.com/rahul-prasad-007/Background-Remover

## Option A — Docker on a VPS (recommended)

Needs a Linux VPS with **≥6–8 GB RAM** (DigitalOcean, Hetzner, Lightsail, etc.).

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
# edit backend/.env if needed

docker compose up -d --build
```

Open `http://YOUR_SERVER_IP:8000` — UI + API on the same port.

Optional Nginx (SSL): copy `deploy/nginx.conf` and point it at port 8000, then add Certbot.

## Option B — Render.com (connect GitHub)

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. **New → Blueprint** → select `Background-Remover`
3. Use a plan with **≥4–8 GB RAM** (free tier will crash on PyTorch)
4. Deploy — health check: `/api/health`

`render.yaml` is already in the repo.

## Option C — Split hosting

| Part | Host | Notes |
|---|---|---|
| Frontend | Vercel / Netlify | Root = `frontend`, build = `npm run build`, output = `dist` |
| Backend | Render / Railway / VPS | Docker or `uvicorn app.main:app` |

Set frontend env:

```
VITE_API_URL=https://your-backend.example.com
```

Set backend env:

```
CORS_ORIGINS=https://your-frontend.vercel.app
```

## Local production-like test (no Docker)

```bat
cd frontend
npm install
npm run build
xcopy /E /I dist ..\backend\static

cd ..\backend
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

## Important

- First request downloads AI models (slow once).
- Use **1 Uvicorn worker** only.
- Prefer UI quality **Original** or **2×** on small servers.
- Never commit `backend/.env` (secrets).
