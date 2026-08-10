# CarbonPanel release checklist

Managed Web Panel installs track the branch recorded in
`.carbonpanel-release.json` (normally `master`) and compare the installed commit
to that branch tip. GitHub releases and version tags are Android release
artifacts; they are deliberately not used as the Web Panel update source.

## Recommended Web Panel release flow

1. Merge and push the tested changes to the branch managed installs track.
2. Verify a managed panel reports the new branch commit as available.
3. Install from **Settings → Version & Updates** and watch the server-reported
   phase progress through the 60-second backend restart window.
4. Confirm the installed and latest commits match after reload.

A formal version tag and GitHub release can still be published for release notes
or an Android APK, but neither is required for managed Web Panel updates.

## How to publish a GitHub release

### Option A: GitHub web UI

1. Open the repository on GitHub.
2. Click **Releases**.
3. Click **Draft a new release**.
4. Choose the existing tag, for example `v0.1.0`.
5. Set the release title, for example:
   - `CarbonPanel v0.1.0`
6. Paste release notes.
7. Click **Publish release**.

### Option B: git tag first, then release

If the tag does not exist yet:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then use the GitHub UI to publish the release for that tag.

## What to put in release notes

A good release body should include:

### 1. Summary
A short explanation of what changed overall.

Example:

```text
CarbonPanel v0.1.0 adds the new interactive installer, systemd-based update checks, rollback support, and in-app release visibility.
```

### 2. Highlights
List the main user-visible improvements.

Example:

```text
- Added GitHub-based installer for production servers
- Added in-app version display and update actions
- Added daily release checks
- Added rollback support for failed upgrades
```

### 3. Upgrade notes
Anything admins should know before updating.

Example:

```text
Upgrade notes:
- Source installs now live under /opt/carbonpanel
- nginx serves the frontend and proxies /api and /ws
- A daily systemd timer checks the tracked GitHub branch tip
```

### 4. Breaking changes
If none, explicitly say so.

Example:

```text
Breaking changes:
- None
```

### 5. Rollback notes
If an update is safe to roll back, say that.

Example:

```text
Rollback:
- Source installs can roll back to the previous release automatically if startup fails
- SQLite databases are backed up before upgrade during managed installs
```

## Example release template

```text
## Summary
Short summary of the release.

## Highlights
- Feature 1
- Feature 2
- Fix 1

## Upgrade notes
- Note anything special required before/after updating

## Breaking changes
- None

## Rollback
- Managed installs can automatically roll back on failed startup
```

## Android release workflow

The Android release workflow only publishes an APK when both conditions hold:

1. The pushed tag is exactly vMAJOR.MINOR.PATCH.
2. The diff from the previous v* tag includes a file under android/.

versionCode and versionName are derived from the tag in CI. Do not add a
GitHub Actions paths filter to tag pushes; the workflow's check job performs
the Android diff explicitly. A skipped Android build is a successful release,
and the next tag still compares against the previous tag.

After publishing, verify the asset:

~~~bash
gh release view v0.1.0 --json assets -q '.assets[].name'
~~~

## Notes about assets

You do **not** need to upload panel release assets manually. When Android
changed, CI builds, signs, and attaches the APK automatically.

The managed Web Panel installer resolves its recorded branch, compares commit
IDs, and builds the backend and frontend from that branch on the target server.
It does not consume the newest GitHub release or automatically switch to a tag.

The Android release workflow is tag-driven and attaches the signed APK to the
matching GitHub release when `android/` changed.

## Recommended version naming

Use semantic version tags:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

This works well with GitHub releases and makes update history easier to read.
