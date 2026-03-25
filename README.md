# CarbonPanel

![Project Status](https://img.shields.io/badge/status-active-00C853?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

CarbonPanel is a lightweight **self-hosted** server monitoring panel built with **FastAPI** and **Vue 3**. It provides a clean dashboard for live system metrics, basic site/service management, and account settings with optional TOTP-based 2FA.

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

CarbonPanel is intended as a self-hosted app. The Docker setup builds a **single image** containing the Vue frontend, nginx, and the FastAPI backend.

1. Copy the backend environment file:

```bash
cp /home/leodeng/Desktop/CarbonPanel/backend/.env.example /home/leodeng/Desktop/CarbonPanel/backend/.env
```

2. Build the image:

```bash
docker build -t carbonpanel /home/leodeng/Desktop/CarbonPanel
```

3. Run it directly with Docker:

```bash
docker run -d \
  --name carbonpanel \
  --network host \
  --restart unless-stopped \
  --env-file /home/leodeng/Desktop/CarbonPanel/backend/.env \
  -v /home/leodeng/Desktop/CarbonPanel/backend/carbonpanel.db:/app/carbonpanel.db \
  carbonpanel
```

Or run it with Docker Compose:

```bash
docker compose up --build -d
```

With the default setup, the app is available at `http://localhost`.

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

Run the self-hosted app with Docker Compose:

```bash
docker compose up --build
```

Default URL:

- App: `http://localhost`

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