# Deploy guide

## Hugging Face Spaces (recommended free path)

Full click-by-click instructions are in the root **[README.md](README.md#hugging-face-spaces-deployment-free)**.

Summary:

1. Push this repo to GitHub (`main`).
2. Create a Space with **Docker** SDK at https://huggingface.co/new-space
3. Link GitHub repo `rahul-prasad-007/Background-Remover`
4. Wait for build → open the Space URL (port **7860** inside the container)

## Docker Compose (VPS)

```bash
git clone https://github.com/rahul-prasad-007/Background-Remover.git
cd Background-Remover
cp backend/.env.example backend/.env
docker compose up -d --build
```

Open `http://YOUR_SERVER_IP:8000` (compose maps 8000; Spaces uses 7860).

> Note: `docker-compose.yml` still publishes host port **8000**.  
> The image itself listens on **`$PORT` (default 7860)** for Hugging Face.

To run the HF image locally on 7860:

```bash
docker build -t shankar-card-ai .
docker run --rm -p 7860:7860 shankar-card-ai
```

## Render.com

Use `render.yaml` → Dashboard → New → Blueprint. Needs **≥4–8 GB RAM**.
