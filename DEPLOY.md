# Generic deploy notes

For **Oracle Cloud Always Free (recommended)**, follow **[DEPLOY_ORACLE.md](DEPLOY_ORACLE.md)**.

## Docker Compose (any VPS)

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
docker compose up -d --build
```

- Public UI/API: **http://YOUR_IP/** (Nginx → port 80)
- Health: **http://YOUR_IP/api/health**
- Containers use `restart: unless-stopped` (survive reboot when Docker is enabled)

## Render.com

See `render.yaml`. Needs a plan with enough RAM for PyTorch (free tier usually OOMs).

## Requirements

- ≥8 GB RAM recommended
- Docker Engine + Compose plugin
- Outbound HTTPS for first-time model downloads
