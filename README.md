<p align="center"><img src="assets/branding/carbonpanel-logo.svg" width="160" alt="CarbonPanel logo" /></p>

# CarbonPanel

![Project Status](https://img.shields.io/badge/status-active-00C853?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/leodenglovescode/CarbonPanel?style=for-the-badge)
![GitHub last commit](https://img.shields.io/github/last-commit/leodenglovescode/CarbonPanel?style=for-the-badge)
<br/><br/>
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)

A lightweight, self-hosted server monitoring panel. No bs, no paywall.

Monitor CPU, memory, GPU, disks, network traffic, and processes from a web
browser or the native Android app. Manage services and sites, browse files,
and install panel updates from the web interface.

<img width="1279" height="634" alt="CarbonPanel dashboard" src="https://github.com/user-attachments/assets/b37ce570-fb52-4935-8827-30ce5b3d1d16" />

## Install

The native installer sets up CarbonPanel with nginx and a systemd or SysV
service. Requires root, Debian/Ubuntu, Python 3.11+, and Node.js 18+.

```bash
curl -fsSL https://carbonpanel.leodeng.dev/install.sh | sudo bash
```

When already logged in as root, omit `sudo`.

Initial credentials are saved to `/opt/carbonpanel/shared/first-install.txt`.
On first login, set a new password and optionally enable two-factor authentication.

The installer enables HTTPS with a self-signed certificate. For a publicly
trusted connection, configure a certificate for the server's domain. Passkeys
require a stable domain hostname and a certificate trusted by the device;
accepting a self-signed certificate warning is not sufficient. TOTP is also
available when passkeys cannot be used.

CarbonPanel manages the host it runs on, including services, processes, disks,
and nginx sites. The native installer is the supported deployment method.
The retained `docker/` nginx snippets are legacy integration helpers, not a
standalone deployment.

## Features

- **Live monitoring** — CPU, memory, GPU, disk, network, and process metrics over WebSocket.
- **NAS monitoring** — read-only Linux software RAID, LVM, and fan/PWM status where exposed by the kernel.
- **Service management** — browse, start, stop, restart, enable, and disable supported services.
- **Sites and apps** — manage tracked services, inspect logs and configuration, and identify listening ports.
- **Disk tools** — partition information, filesystem checks, and unmounting removable storage.
- **Read-only file browser** — list/grid views, path navigation, search, sorting, previews, and downloads on web and Android. No file editing or deletion.
- **Customizable dashboard** — automatic card placement or a saved manual layout, themes, backgrounds, colors, fonts, and surface transparency.
- **Account security** — revocable sessions, optional TOTP two-factor authentication, passkeys on trusted HTTPS hostnames, and HTTPS-only Android connections.
- **In-panel updates** — check for releases, follow installation progress, and recover with automatic rollback on failed deployment or health checks.

Settings are grouped into General, Appearance, Notifications, Account & security,
and Server, with search across all groups. Automatic placement is under
**Settings → General → Dashboard layout**.

The file browser uses the CarbonPanel service account's filesystem permissions.
Images, audio, and video preview where supported by the client; Markdown and code
files have formatted previews. Text previews are limited to 1 MiB, while larger
files can still be downloaded. See the [file browser details](docs/file-browser-ux.md)
and [NAS compatibility guide](docs/NAS.md) for capabilities and limitations.

## Android app

Download the APK from [GitHub Releases](https://github.com/leodenglovescode/CarbonPanel/releases/latest).

To connect, open **Settings → Account & security → Paired Devices** in the web
panel and scan the pairing QR code with the Android app. Pairing supports
HTTPS endpoints and binds the installer's self-signed certificate to the device.

The native app supports multiple servers, monitoring widgets, file previews,
and downloads through Android's save picker. Server backgrounds are shared
with the panel; the server chooser background is configured locally in the app.

![Android app screenshots using demo data](assets/store/screenshots/contact-sheet.png)

[F-Droid submission](https://gitlab.com/fdroid/fdroiddata/-/merge_requests/56044)
· [Android setup and development](android/README.md)

## Updating

Use **Settings → Server → Updates & service logs → Install Update**, or run:

```bash
sudo carbonpanelctl update
```

The panel displays installation progress and reconnects after the service restarts.
Failed deployment or health checks trigger an automatic rollback. To roll back
manually:

```bash
sudo carbonpanelctl rollback
```

## Configuration

Local development reads `backend/.env`; managed installations read
`/opt/carbonpanel/shared/backend.env`. The installer generates production secrets
and initial credentials.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | Development placeholder | JWT signing key; use a unique random secret in production |
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | `changeme` (development) | Initial password; the installer generates a random password, and updates preserve existing accounts |
| `APP_PORT` | `8787` | Installer setting for the nginx HTTPS port |
| `COOKIE_SECURE` | `true` (installer), `false` (development) | Require HTTPS for session cookies |
| `TLS_CERT_FILE` | Unset in development | PEM certificate used to bind Android pairing to the server's TLS certificate |
| `DATABASE_URL` | `sqlite+aiosqlite:///./carbonpanel.db` | Database connection string |
| `METRICS_INTERVAL_SECONDS` | `2.0` | Metrics collection interval |
| `PROCESS_LIMIT` | `25` | Maximum processes displayed |

## Local development

```bash
make setup   # install dependencies, generate secrets, migrate DB, seed admin
make dev     # start backend and frontend with automatic reload
```

| URL | Service |
|---|---|
| `http://localhost:5174` | Frontend (Vite) |
| `http://localhost:8010/api/v1` | Backend API |

`make dev` applies pending database migrations and stops both services when either
exits or Ctrl+C is pressed. HTTP is available for development; installed panels
use HTTPS.

Other commands: `make backend`, `make frontend`, `make lint`.

## Technical documentation

- [Android client](android/README.md)
- [Android build reproducibility](docs/android-reproducibility.md)
- [F-Droid build and update configuration](fdroid/README.md)
- [Brand assets](assets/branding/README.md)
- [Store screenshots](assets/store/README.md)

**Backend:** Python, FastAPI, SQLAlchemy, Alembic, SQLite, psutil.
**Frontend:** Vue 3, TypeScript, Vite, Pinia, Chart.js.
**Android:** Kotlin, Jetpack Compose, Retrofit, Glance.

Idea and logic by @leodenglovescode, code assisted by AI.
