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
First login walks you through an onboarding wizard to set a real password and optionally
enable 2FA.

> CarbonPanel manages the host it runs on — systemd services, real process/disk access,
> nginx sites — so the supported production path is the native systemd installer. The
> retained `docker/` nginx snippets are legacy integration helpers only; they require an
> external TLS-terminating proxy and are not a standalone deployment.

nginx serves the panel over HTTPS with a self-signed certificate generated at install time
(covering the server's hostname and detected IPs). Your browser will warn that it isn't
trusted — that's expected for a self-signed cert; click through it (Chrome: "Advanced" →
"Proceed"). It's still real TLS encryption, just not backed by a public CA, which is a lot
better than the plaintext HTTP this used to default to.

---

## Updating

Use the **Settings → Install Update** button in the panel, or SSH in and run:

```bash
sudo carbonpanelctl update
```

The Web UI follows the specific update job it starts and displays server-reported
progress for each real phase (system packages, backend/frontend dependencies,
build, migration, deployment, and health check). Immediately before the backend
restarts, it shows a 60-second countdown and reloads automatically when the
restart window ends. Historical service logs are diagnostic only and never
advance the progress bar.

Update checks and installs are serialized so a timer cannot overwrite an
interactive result. Each manual check is matched to its own result instead of
reusing stale status. Updates auto-rollback on failed deployment or health check.
To roll back manually: `sudo carbonpanelctl rollback`.

---

## Configuration

Local development reads `backend/.env`; managed installs read
`/opt/carbonpanel/shared/backend.env`.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-...` | JWT signing key — **change this in production** |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `changeme` | Initial admin password; updates never reset an existing account |
| `APP_PORT` | `8787` | Port nginx listens on (HTTPS) |
| `COOKIE_SECURE` | `true` (install script) / `false` (local default) | Marks the session cookie HTTPS-only |
| `TLS_CERT_FILE` | unset (local) | PEM certificate whose SHA-256 fingerprint is embedded in Android pairing QR codes |
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
- **HTTPS by default** — self-signed cert generated at install time, no plaintext credentials on the wire
- **Guided onboarding** — first login walks through setting a password and 2FA setup
- **Native Android client** — HTTPS-only bearer auth; installer self-signed certificates are pinned from the pairing QR
- **In-panel updates** — version check via GitHub API, one-click update from the Settings page

---

## Local Development

```bash
make setup   # generate secrets, install locked deps, migrate DB, seed admin
make dev     # run backend + frontend together
```

| URL | Service |
|---|---|
| `http://localhost:5173` | Frontend (Vite HMR) |
| `http://localhost:8010/api/v1` | Backend API |

Other commands: `make backend`, `make frontend`, `make lint`

---

## Tech Stack

**Backend** — Python 3.11+, FastAPI, SQLAlchemy + Alembic, SQLite (aiosqlite), psutil

**Frontend** — Vue 3, TypeScript, Vite, Pinia, Chart.js

---

Idea and logic by @leodenglovescode, code assisted by Claude Code.
