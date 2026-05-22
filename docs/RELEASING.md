# CarbonPanel release checklist

CarbonPanel updates are designed to track **GitHub releases first**, then **git tags**, then the default branch only as a fallback.

## Recommended release flow

1. Make sure `backend/pyproject.toml` has the new app version.
2. Optionally keep `frontend/package.json` aligned to the same version.
3. Merge your changes into the branch you release from.
4. Create and push a git tag:
   - `git tag v0.1.0`
   - `git push origin v0.1.0`
5. Publish a GitHub release for that tag.
6. CarbonPanel servers can then detect the new release during their daily check.

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
- A daily systemd timer checks GitHub releases
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

## Notes about assets

You do **not** need to upload release assets for the current installer flow.

The installer:
- resolves the newest GitHub release,
- checks out the release tag from GitHub,
- builds the backend and frontend from source on the target server.

That means a clean tag plus a published GitHub release is enough.

## Recommended version naming

Use semantic version tags:

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

This works well with GitHub releases and makes update history easier to read.
