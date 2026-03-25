# CarbonPanel

![Project Status](https://img.shields.io/badge/status-active-00C853?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/leodenglovescode/CarbonPanel?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/leodenglovescode/CarbonPanel?style=for-the-badge)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/leodenglovescode/CarbonPanel/publish-docker.yml?style=for-the-badge)
<br/><br/>
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

CarbonPanel is a lightweight **self-hosted** server monitoring panel built with **FastAPI** and **Vue 3**. It provides a clean dashboard for live system metrics, basic site/service management, and account settings with optional TOTP-based 2FA.

## Screenshots
<img width="960" height="479" alt="image" src="https://github.com/user-attachments/assets/5b713832-5792-4972-8675-0403242c5f69" />

## Features

- Live dashboard for **CPU, RAM, GPU, disk, network, process, and system** metrics
- Real-time updates over **WebSocket**
- **JWT authentication** with optional **TOTP 2FA**
- Manage tracked sites/services with support for:
  - service actions
  - config file read/write
  - log streaming
- Adjustable metric refresh interval and process display limits
- SQLite-backed backend with Alembic migrations
- Local development workflow via `make`
- Docker support for running the full self-hosted stack as a single image

## Tech Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy + Alembic
- SQLite (`aiosqlite`)
- psutil

### Frontend
- Vue 3
- TypeScript
- Vite
- Pinia
- Chart.js

## Project Structure

```text
.
├── backend/     # FastAPI app, database models, API routes, services, migrations
├── docker/      # nginx config and startup script for the combined image
├── frontend/    # Vue 3 app, widgets, pages, stores, API client
├── Dockerfile   # combined frontend + backend container image
├── Makefile     # local setup and dev commands
└── docker-compose.yml
```

## Quick Start

### Docker / self-hosted deployment

CarbonPanel is intended as a self-hosted app. The published GHCR package is a **single image** containing the Vue frontend, nginx, and the FastAPI backend.

1. Copy the backend environment file:

```bash
cp /home/leodeng/Desktop/CarbonPanel/backend/.env.example /home/leodeng/Desktop/CarbonPanel/backend/.env
```

2. Pull the latest image from GHCR:

```bash
docker pull ghcr.io/leodenglovescode/carbonpanel:latest
```

3. Run it directly with Docker:

```bash
docker run -d \
  --name carbonpanel \
  --network host \
  --restart unless-stopped \
  -e APP_PORT=8787 \
  --env-file /home/leodeng/Desktop/CarbonPanel/backend/.env \
  -v /home/leodeng/Desktop/CarbonPanel/backend/carbonpanel.db:/app/carbonpanel.db \
  ghcr.io/leodenglovescode/carbonpanel:latest
```

> Default app port is `8787`. Change `APP_PORT` if you want CarbonPanel to listen on a different port, including when using `--network host`.

Or run it with Docker Compose after changing the service to use the published image instead of `build`:

```bash
docker compose up -d
```

With the default setup, the app is available at `http://localhost:8787`.

### Local development

1. Copy environment files:

```bash
cp /home/leodeng/Desktop/CarbonPanel/backend/.env.example /home/leodeng/Desktop/CarbonPanel/backend/.env
cp /home/leodeng/Desktop/CarbonPanel/frontend/.env.example /home/leodeng/Desktop/CarbonPanel/frontend/.env
```

2. Install and initialize everything:

```bash
make setup
```

3. Start both apps:

```bash
make dev
```

### Default local URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/v1`

## Docker

Pull and run the latest published image:

```bash
docker pull ghcr.io/leodenglovescode/carbonpanel:latest
docker run -d \
  --name carbonpanel \
  --network host \
  --restart unless-stopped \
  -e APP_PORT=8787 \
  --env-file /home/leodeng/Desktop/CarbonPanel/backend/.env \
  -v /home/leodeng/Desktop/CarbonPanel/backend/carbonpanel.db:/app/carbonpanel.db \
  ghcr.io/leodenglovescode/carbonpanel:latest
```

> Default app port: `8787`. Set `APP_PORT` to override it. This is especially useful with `network_mode: host`, where port publishing with `-p` does not apply.

If you prefer Docker Compose, use an image-based service definition like this:

```bash
services:
  carbonpanel:
    image: ghcr.io/leodenglovescode/carbonpanel:latest
    env_file:
      - ./backend/.env
    environment:
      APP_PORT: ${APP_PORT:-8787}
    volumes:
      - ./backend/carbonpanel.db:/app/carbonpanel.db
    restart: unless-stopped
    network_mode: host
```

Then start it with:

```bash
docker compose up -d
```

Default URL:

- App: `http://localhost:8787`

> Note: the container uses `network_mode: host` so system/network metrics can reflect the host more accurately.

## Configuration

### Backend

The backend reads settings from `backend/.env`. Important variables include:

- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `DATABASE_URL`
- `CORS_ORIGINS`
- `METRICS_INTERVAL_SECONDS`
- `PROCESS_LIMIT`

The first-time setup seeds an admin user from the configured `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

### Frontend

The frontend reads from `frontend/.env`:

- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

For local Vite development, these can be left blank as noted in `.env.example`.

## Available Commands

```bash
make setup     # create venv, install backend/frontend deps, migrate DB, seed admin
make dev       # run backend and frontend together
make backend   # run backend only
make frontend  # run frontend only
```

## API Overview

- REST API prefix: `/api/v1`
- Auth routes: `/auth/*`
- Settings routes: `/settings/*`
- Sites routes: `/sites/*`
- WebSocket endpoints are mounted separately from the REST prefix

## Notes

- Default database: SQLite (`backend/carbonpanel.db`)
- Metrics collection starts with the FastAPI app lifespan
- The dashboard is auth-protected; unauthenticated users are redirected to `/login`

Idea and logic by @leodenglovescode, Code assisted by Claude Code & GPT-5.4
