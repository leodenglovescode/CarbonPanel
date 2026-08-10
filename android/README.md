# CarbonPanel for Android

Native Kotlin/Jetpack Compose client for a CarbonPanel server. It renders
locally and talks to the API over HTTPS; it is not a WebView.

## Build

~~~bash
cd android
./gradlew :app:assembleDebug
./gradlew installDebug
~~~

The debug APK is written to app/build/outputs/apk/debug/app-debug.apk. Building
requires JDK 17+ and an Android SDK with platform 36. local.properties must set
sdk.dir to the local SDK path.

## Pairing and authentication

The app has no password login screen. Pairing starts in the authenticated web
panel:

1. Open **Settings → Paired Devices**.
2. Re-enter the current password and, when enabled, the current TOTP code.
3. Select one or more HTTPS server addresses and generate the QR.
4. Scan the QR in the Android app.
5. The app exchanges the five-minute, single-use code for a 90-day bearer
   token represented by a revocable device row.

The QR contains compact fields for its version, one-time code, endpoint list,
server name, optional SHA-256 TLS certificate fingerprint, and the hosts to
which that fingerprint applies: {v, c, e, n, f, p}. Passwords and TOTP codes
never enter the QR or the phone.

Revoke the Android token from **Settings → Active Sessions**. Revocation takes
effect immediately for request/response calls and open streams.

## Endpoints

Pairing can include multiple HTTPS endpoints because a LAN address may stop
working when the phone leaves home. Operator-configured public or overlay
addresses are tried first, followed by the current browser address and local
interfaces. The app remembers the last working address and tries it first next
time.

Add or change endpoints in the web panel, then re-pair so the phone receives
the updated authenticated list and certificate binding. Android does not allow
adding arbitrary endpoints after pairing.

## TLS and self-signed certificates

Cleartext traffic is disabled in both the manifest and network security
configuration. The bearer token is never sent over HTTP, including private LAN
and VPN addresses.

Publicly trusted HTTPS certificates use Android's system CA validation.
Managed installs use a self-signed certificate; the backend embeds its SHA-256
fingerprint in the QR. The app stores that fingerprint for every QR endpoint
before making the first request and requires an exact match. There is no
trust-on-first-use fallback.

Manual code entry is only suitable for a publicly trusted HTTPS certificate,
because it cannot carry the self-signed certificate fingerprint. An endpoint
whose host is absent from the configured certificate's subject alternative
names also needs publicly trusted TLS; the backend only attaches the QR pin to
hosts that the certificate identifies. If a managed install's certificate is
intentionally replaced, re-pair the device.

Pairing payload version 2 introduced HTTPS-only, QR-bound certificate trust.
After upgrading from an older HTTP-capable app, re-pair if the saved endpoint
list contains no usable HTTPS address.

## Battery model

- **Foreground:** request/response polling with a selectable interval down to
  0.4 seconds. Collection stops when no UI observes it.
- **Background:** no persistent service or socket. WorkManager refreshes the
  home-screen widget at Android's supported periodic interval.
- Dashboard requests omit the process table unless that screen needs it.

## App scope

The native client includes status, Docker containers, system services, disks,
sites, cron jobs, listening ports, processes, shell sessions, bookmarks,
webhooks, update logs, appearance/widget settings, device revocation, and
server connectivity controls. Password and 2FA management remain in the web
panel.

## Toolchain notes

AGP 9 has built-in Kotlin support; do not also apply
org.jetbrains.kotlin.android. Release versions come from vMAJOR.MINOR.PATCH
tags in CI, and an APK is produced only when Android files changed since the
previous tag.
