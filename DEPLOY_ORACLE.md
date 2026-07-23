# Deploy on Oracle Cloud Always Free (Ubuntu + Docker)

This guide deploys **Shankar Card AI Image Enhancer** (React + FastAPI) on an
**Oracle Cloud Infrastructure (OCI) Always Free** Ubuntu VM using Docker Compose.

Public URL is served on **port 80** (Nginx → FastAPI, which also serves the React UI).

Repository: https://github.com/rahul-prasad-007/Background-Remover

---

## Important: choose the right Always Free shape

| Shape | RAM | Suitable? |
|---|---|---|
| **VM.Standard.A1.Flex (Ampere ARM)** — 2–4 OCPU, **8–24 GB RAM** | Recommended | Yes — this stack needs RAM for PyTorch / rembg |
| VM.Standard.E2.1.Micro | **1 GB** | **No** — will OOM / crash |

Create an **Ampere A1** instance with at least **8 GB RAM** (24 GB if available).

Architecture notes:
- Ampere = **aarch64** — our Docker images support it (multi-arch official bases + CPU PyTorch wheels).
- First run downloads BiRefNet / Real-ESRGAN / YuNet weights into a Docker volume (can take several minutes).

---

## Quick start (after the VM exists)

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
# optional: nano backend/.env
docker compose up -d --build
```

Then open: `http://YOUR_PUBLIC_IP/`

Health check: `http://YOUR_PUBLIC_IP/api/health`

---

## 1. Create an Oracle Cloud Always Free Ubuntu VM

1. Sign in to [Oracle Cloud Console](https://cloud.oracle.com/).
2. **Compute → Instances → Create instance**.
3. Settings:
   - **Name:** `shankar-card-ai` (any name)
   - **Image:** Canonical Ubuntu **22.04** or **24.04**
   - **Shape:** `VM.Standard.A1.Flex` (Ampere)
     - OCPUs: `2` or `4`
     - Memory: **`8` GB minimum** (prefer `16–24` GB)
   - **Networking:** create / select a VCN with a public subnet; assign a **public IP**
   - **SSH keys:** paste your public key (`~/.ssh/id_rsa.pub` or generate one)
4. Click **Create**.
5. Note the **Public IP address**.

SSH in:

```bash
ssh -i /path/to/your-key ubuntu@YOUR_PUBLIC_IP
```

(On some images the user is `opc` — use whichever the console shows.)

---

## 2. Open firewall ports (80, 443, 22)

### A) OCI Security List / NSG (required)

1. **Networking → Virtual Cloud Networks → your VCN → Security Lists** (or NSG on the subnet/instance).
2. **Ingress Rules** — add:

| Source | Protocol | Ports |
|---|---|---|
| `0.0.0.0/0` | TCP | **22** |
| `0.0.0.0/0` | TCP | **80** |
| `0.0.0.0/0` | TCP | **443** |

### B) Ubuntu firewall (if `ufw` / `iptables` blocks traffic)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Oracle Ubuntu images sometimes use `iptables-nft` / `firewalld`. If UFW is inactive, also check:

```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
```

---

## 3. Install Docker and Docker Compose

On the Ubuntu VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow your user to run Docker without sudo (re-login after)
sudo usermod -aG docker "$USER"
newgrp docker

docker --version
docker compose version
```

Enable Docker on boot (auto-restart containers after reboot):

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

Compose uses `restart: unless-stopped` so containers come back after reboot when Docker starts.

---

## 4. Clone the GitHub repository

```bash
cd ~
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
```

---

## 5. Set up the `.env` file

```bash
cp backend/.env.example backend/.env
nano backend/.env   # optional
```

Defaults are tuned for Always Free (local BiRefNet, low memory profile, unload models after use).

Useful knobs:

| Variable | Meaning |
|---|---|
| `BG_PROVIDER=local` | Free unlimited local cutout |
| `SAFE_INPUT_SIDE` | Cap input size (lower = less RAM) |
| `REALESRGAN_TILE` | Smaller = less peak RAM |
| `CORS_ORIGINS=*` | Fine for same-origin Nginx setup |
| `REMOVE_BG_API_KEY` | Only if `BG_PROVIDER=removebg` |

Optional memory limit for the app container (in the shell before compose, or export permanently):

```bash
export APP_MEM_LIMIT=12g   # if your Ampere VM has 24 GB
```

---

## 6. Build and run the project

```bash
cd ~/Background-Remover
docker compose up -d --build
```

First build downloads base images + pip packages (can take **10–30+ minutes** on Ampere).

Watch progress:

```bash
docker compose ps
docker compose logs -f app
```

Wait until health is healthy:

```bash
docker compose ps
curl -fsS http://127.0.0.1/api/health
```

---

## 7. Verify the deployment

From your laptop:

```bash
curl http://YOUR_PUBLIC_IP/api/health
```

Expected JSON similar to:

```json
{"status":"ok","service":"Shankar Card AI Image Enhancer"}
```

In a browser open:

- `http://YOUR_PUBLIC_IP/` — full UI
- Upload a test image and run **Original** or **2×** first (lighter than 4×)

First AI request downloads models into the `app-weights` volume — progress may sit on “Removing Background…” for a few minutes once.

---

## 8. Nginx reverse proxy (already included)

`docker compose` starts:

| Service | Role |
|---|---|
| `app` | FastAPI + React static files on internal `:8000` |
| `nginx` | Public **:80** / **:443** → proxies to `app` |

Config file: `deploy/nginx.conf`  
SSE / long AI jobs: `proxy_read_timeout 600s`, `proxy_buffering off` for `/api/`.

Reload Nginx after config edits:

```bash
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

---

## 9. HTTPS with Let's Encrypt + Certbot

### Prerequisites

- A **domain name** pointing to `YOUR_PUBLIC_IP` (A record)
- Ports **80** and **443** open in OCI + Ubuntu firewall

### Issue a certificate (webroot)

Find your Compose project volume names:

```bash
docker volume ls | grep certbot
```

Typical names (project folder `Background-Remover`):

- `background-remover_certbot-www`
- `background-remover_certbot-certs`

Issue cert (replace domain, email, and volume names if different):

```bash
cd ~/Background-Remover

docker run --rm \
  -v background-remover_certbot-www:/var/www/certbot \
  -v background-remover_certbot-certs:/etc/letsencrypt \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d YOUR_DOMAIN.com \
  --email YOUR_EMAIL@example.com \
  --agree-tos --no-eff-email
```

If volume names differ, copy them exactly from `docker volume ls`.

### Enable SSL in Nginx

```bash
cd ~/Background-Remover
cp deploy/nginx-ssl.conf.example deploy/nginx.conf
nano deploy/nginx.conf   # replace ALL YOUR_DOMAIN with your real domain
docker compose up -d nginx
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

Visit: `https://YOUR_DOMAIN.com`

### Auto-renewal (cron)

```bash
sudo crontab -e
```

Add:

```cron
0 3 * * * docker run --rm -v background-remover_certbot-www:/var/www/certbot -v background-remover_certbot-certs:/etc/letsencrypt certbot/certbot renew --webroot -w /var/www/certbot && cd /home/ubuntu/Background-Remover && docker compose exec -T nginx nginx -s reload
```

Adjust username/path/volume names to match your VM.

---

## 10. Custom domain (optional)

1. At your DNS provider, create an **A record**:
   - Host: `@` (or `app`)
   - Value: `YOUR_PUBLIC_IP`
   - TTL: 300
2. Wait for DNS propagation (`dig YOUR_DOMAIN.com`).
3. Set in `backend/.env`:

   ```env
   CORS_ORIGINS=https://YOUR_DOMAIN.com
   ```

4. Restart app:

   ```bash
   docker compose up -d app
   ```

5. Complete HTTPS steps in section 9.

---

## 11. Update after future GitHub commits

```bash
cd ~/Background-Remover
git pull origin main
docker compose up -d --build
```

Volumes (`uploads`, `outputs`, `weights`) are preserved — models are not re-downloaded unless the volume is removed.

Rollback to a previous commit if needed:

```bash
git log --oneline -5
git checkout COMMIT_SHA
docker compose up -d --build
```

---

## 12. Troubleshooting

### `curl` to public IP fails / timeout

- Check OCI **Security List** ingress for 80/443/22
- Check `sudo ufw status` / iptables
- Confirm instance has a **public IP** and is running
- `docker compose ps` — nginx should be `Up`

### Build fails / pip or torch errors on Ampere

- Ensure shape is **A1 Flex** with enough free disk (`df -h` — need **≥20 GB** free)
- Retry: `docker compose build --no-cache app`
- Confirm arch: `uname -m` → `aarch64`

### Container killed / exit 137 / OOM

- Increase Ampere memory (edit instance shape)
- Lower in `backend/.env`:
  - `SAFE_INPUT_SIDE=1280`
  - `BIREFNET_MAX_SIDE=640`
  - `REALESRGAN_TILE=96`
- Prefer UI quality **Original** or **2×**
- Lower `APP_MEM_LIMIT` only if the host has less RAM; do not set it higher than free RAM

### `/api/health` OK but UI blank

- Confirm frontend was baked into the image:  
  `docker compose exec app ls /app/static/index.html`
- Rebuild: `docker compose up -d --build`

### Background removal stuck on first run

- Normal while BiRefNet downloads to `~/.u2net` inside the container / weight caches  
- Watch: `docker compose logs -f app`
- Ensure outbound HTTPS is allowed from the VCN (default yes)

### Upload / file size errors

- Max size is `MAX_FILE_SIZE_MB` (default 20)
- Nginx `client_max_body_size 25m` — raise both if needed

### SSE progress never updates

- Nginx must keep `proxy_buffering off` on `/api/` (already set)
- Don’t put another buffering CDN in front without SSE support

### After reboot, site down

```bash
sudo systemctl status docker
docker compose -f ~/Background-Remover/docker-compose.yml ps
cd ~/Background-Remover && docker compose up -d
```

Docker + `restart: unless-stopped` should auto-start containers once Docker is enabled.

### View logs

```bash
docker compose logs -f --tail=200 app
docker compose logs -f --tail=100 nginx
```

### Full reset (destructive)

```bash
docker compose down
# WARNING: deletes uploaded/result/model volumes
docker compose down -v
docker compose up -d --build
```

---

## Architecture (production)

```
Internet
   │
   ▼
Nginx (:80 / :443)          ← docker service "nginx"
   │
   ▼
FastAPI + React static      ← docker service "app" (:8000 internal)
   │
   ├─ /api/process (SSE)
   ├─ /api/download/{id}
   ├─ /api/health
   └─ /  (React UI from /app/static)
```

Models: BiRefNet (rembg), YuNet face detect, Real-ESRGAN (torch), optional GFPGAN path (OpenCV fallback when `USE_GFPGAN_MODEL=false`).

---

## Security notes

- Never commit `backend/.env`
- Uploads are stored under random `job_id` names; download paths are sanitized
- Prefer HTTPS + domain for any public use
- Restrict SSH (`22`) to your IP in OCI Security Lists when possible

---

## One-liner recap

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
docker compose up -d --build
```

Open `http://YOUR_PUBLIC_IP/`
