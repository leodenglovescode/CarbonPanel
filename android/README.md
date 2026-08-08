# CarbonPanel for Android

Native Kotlin/Compose client for a CarbonPanel server. Renders locally and
talks to the panel over plain HTTP — no WebView, no embedded web UI.

## Build

```bash
cd android
./gradlew :app:assembleDebug        # → app/build/outputs/apk/debug/app-debug.apk
./gradlew installDebug              # to a connected device
```

Requires JDK 17+ and an Android SDK with platform 36. `local.properties` must
point at the SDK (`sdk.dir=/path/to/Android/Sdk`); it is gitignored because the
path is per-machine.

## How pairing works

There is no login screen. The phone never sees a password or a TOTP code.

1. In the web panel: **Settings → Paired Devices → Pair a device**.
2. The server generates a single-use code (5 minute lifetime) and renders it as
   a QR containing `{v, c, e, n}` — version, code, **endpoint list**, server name.
3. The app scans it and `POST`s the code to `/api/v1/pairing/claim`, receiving a
   90-day bearer token scoped to a revocable device row.
4. Revoke any time from the same settings page; revocation takes effect
   immediately.

### Why the QR carries a list of endpoints

The server only knows the address *your browser* used to reach it — usually a
LAN IP. A phone that leaves the house can't use that. So pairing hands over
every address the server believes it has, ordered by how likely they are to
work from elsewhere:

| kind | example | notes |
|---|---|---|
| `custom` | `https://panel.example.com` | entered by hand in Settings |
| `overlay` | `100.64.0.2`, `10.99.0.2` | Tailscale / WireGuard — works anywhere |
| `current` | the address the browser used | fast at home |
| `lan` | `192.168.1.x` | home only |
| `public` | routable address | only offered over HTTPS |

`EndpointResolver` tries the last-known-good address first, then walks the list.
Moving between wifi and mobile data re-resolves automatically.

## Battery model

- **Foreground**: HTTP polling, interval selectable down to 0.4s. Collected
  under `SharingStarted.WhileSubscribed`, so it stops when the app leaves the
  screen. No service, no wakelock, no persistent socket.
- **Background**: nothing, except one WorkManager job every 15 minutes to
  refresh the home-screen widget.
- The dashboard requests `fields=cpu,memory,gpu,disks,system` — omitting the
  process table cuts the payload by roughly two thirds.

## TLS and self-signed certificates

Self-hosted panels usually run plain HTTP on a private network or HTTPS with a
self-signed certificate. `TofuTrustManager` handles the latter:

1. Chain validates against system CAs → accept, pin nothing.
2. A fingerprint is already pinned for the host → require an exact match;
   a change is a hard failure.
3. No pin yet → record it and accept (trust on first use).

Cleartext is permitted app-wide in the manifest because
`network-security-config` cannot express "private ranges only" (it matches
hostnames, not CIDR). `ApiClient.isPermittedEndpoint` enforces the narrowing
instead: an `http://` endpoint on a public address is refused.

## Scope

v1 covers **Dashboard**, **Docker**, and **System Services** — glanceable status
plus the two things worth doing from a phone. Settings, Cron and Sites stay in
the web UI.

Not implemented: push notifications (needs a transport decision — ntfy or FCM),
alert rules, log streaming.

## Toolchain notes

AGP 9 has **built-in Kotlin support**; applying `org.jetbrains.kotlin.android`
alongside it is an error. `buildToolsVersion` is pinned so the build doesn't
try to fetch a revision at build time.

`gradle.properties` forces IPv4 and raises HTTP timeouts — needed on networks
where the proxy has no IPv6 transit and `dl.google.com` is slow. Both are safe
to remove elsewhere.
