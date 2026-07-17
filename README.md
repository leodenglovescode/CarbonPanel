# CarbonPanel

![Project Status](https://img.shields.io/badge/status-active-00C853?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/leodenglovescode/CarbonPanel?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/leodenglovescode/CarbonPanel?style=for-the-badge)
<br/><br/>
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)

A lightweight self-hosted server monitoring panel — live CPU, RAM, GPU, disk, network, and process metrics over WebSocket, with service management, disk management, app/port scanning, and JWT + TOTP authentication.

<img width="1279" height="634" alt="Screenshot Of CarbonPanel" src="https://github.com/user-attachments/assets/b37ce570-fb52-4935-8827-30ce5b3d1d16" />



---

## Install

Installs as a native systemd service with nginx. Requires root, Ubuntu/Debian.

```bash
curl -fsSL https://carbonpanel.leodeng.dev/install.sh | sudo bash
```

Initial credentials are saved to `/opt/carbonpanel/shared/first-install.txt` after install.

> CarbonPanel manages the host it runs on — systemd services, real process/disk access,
> nginx sites — so it runs as a native systemd service rather than in a container. A prior
> Docker deployment path has been removed for this reason.

---

## Updating

Use the **Settings → Install Update** button in the panel, or SSH in and run:

```bash
sudo carbonpanelctl update
```

Updates clone the new release, run DB migrations, health-check, and auto-rollback on failure. To roll back manually: `sudo carbonpanelctl rollback`.

---

## Configuration

All settings are written to `backend/.env` (local dev / install script).

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-...` | JWT signing key — **change this in production** |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `changeme` | Initial admin password |
| `APP_PORT` | `8787` | Port nginx listens on |
| `DATABASE_URL` | `sqlite+aiosqlite:///./carbonpanel.db` | Database connection string |
| `METRICS_INTERVAL_SECONDS` | `2.0` | How often metrics are collected |
| `PROCESS_LIMIT` | `25` | Max processes shown in the dashboard |

---

## Features

- Live **CPU, RAM, GPU, disk, network, and process** metrics over WebSocket
- **Disk management** — partition info, filesystem check, unmount (USB/removable only)
- **App/port scanner** — lists all listening ports with process info, custom labels, kill
- **System services** — browse, start/stop/restart, enable/disable, star and reorder
- **Sites** — manage tracked services with log streaming and config file editing
- **Customizable UI** — dark/light/auto theme, custom colors, fonts, gradients, background images
- **JWT auth** with optional **TOTP 2FA**
- **In-panel updates** — version check via GitHub API, one-click update from the Settings page

---

## Local Development

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
make setup   # create venv, install deps, migrate DB, seed admin
make dev     # run backend + frontend together
```

| URL | Service |
|---|---|
| `http://localhost:5173` | Frontend (Vite HMR) |
| `http://localhost:8000/api/v1` | Backend API |

Other commands: `make backend`, `make frontend`, `make lint`

---

## Tech Stack

**Backend** — Python 3.11+, FastAPI, SQLAlchemy + Alembic, SQLite (aiosqlite), psutil

**Frontend** — Vue 3, TypeScript, Vite, Pinia, Chart.js

---

Idea and logic by @leodenglovescode, code assisted by Claude Code.
