# Draft: CarbonPanel F-Droid merge request

**Merge request body prepared locally. A public fdroiddata fork has been created; no merge request has been opened.**
The proposed version `1.6.0` / `10600` is a placeholder for review, not an existing
release or a newly created tag.

## Proposed title

New app: CarbonPanel

## Proposed merge request body

Adds CarbonPanel (`dev.carbonpanel`), a native Android companion for the
open-source CarbonPanel server monitoring panel.

Users pair the app with their own server through a QR code and connect over
HTTPS. Features include CPU, memory, disk, network, and process monitoring;
software RAID and SMART disk readings where exposed by the server; multiple saved servers;
home-screen widgets; and a read-only file browser with previews and downloads.
A running CarbonPanel server is required. There is no required proprietary
hosted service or Google account.

- Source: https://github.com/leodenglovescode/CarbonPanel
- Issue tracker: https://github.com/leodenglovescode/CarbonPanel/issues
- License: MIT
- Minimum Android version: 8.0 / API 26
- Listing text and icon: `fastlane/metadata/android/en-US/` in the source repository
- Build recipe: `metadata/dev.carbonpanel.yml` in this submission

### Purpose and screenshots

The app provides a native Android interface for the CarbonPanel self-hosted
server panel. Its workflow combines QR pairing and certificate pinning with
system monitoring, container/service controls, and permission-limited read-only
file access. A user runs CarbonPanel on their own Linux server or NAS; the app
does not require a proprietary hosted service. This describes its scope, not a
claim that competing apps lack these features.

Screenshots use fictional data and were captured from the actual Android UI.
The upstream Fastlane directory contains six plain captures; the README shows
framed feature images. Add links pinned to the final release commit before posting.

### Inclusion policy timing

The first Android source commit is dated 2026-08-08. Three calendar months elapse
on 2026-11-08. As of 2026-11-06, the age requirement is not yet met; no exception
is claimed. If opened before that date, keep this request in draft and ask that
inclusion wait until the requirement is met.

### Build and future updates

The build uses the `android/` subdirectory. `carbonUnsigned=true` produces an
unsigned APK without reading upstream release-signing environment variables.
Google Play's encrypted dependency metadata is disabled.

The maintainer selected upstream-signature reproducible builds. `Binaries`
references the GitHub release APK; `AllowedAPKSigningKeys` pins the public
certificate fingerprint already used by v1.5.0. Independent local builds passed
signature-copy verification with a test key. The release workflow also checks
a clean unsigned rebuild before publication. F-Droid must still reproduce the
actual GitHub-signed release on its infrastructure.

The prebuild supplies the selected build's version name/code as Gradle
properties. Future updates are detected through the version JSON attached to
successful GitHub Android releases, using `UpdateCheckMode: HTTP` and
`AutoUpdateMode: Version v%v`. Generated build entries therefore select the
matching GitHub tag and use the new version's properties.

### Preliminary checks

The initial source/dependency audit found no known non-free SDK or tracker
matches. All 147 resolved module POMs declared Apache 2.0 or BSD-3-Clause.
Google Play Services, Firebase, ML Kit, Play Billing, and Play Core were absent.
These are preliminary checks, not a guarantee of acceptance or an independent
copyright audit.

Please review the proposed metadata and build recipe for inclusion.

## Internal preparation notes — exclude from the submitted body

Before approval and posting:

- Choose and publish the first release carrying these changes. Replace the
  provisional version/tag in the metadata if needed. The v1.5.0 release has no
  version JSON and includes encrypted dependency metadata; it is not the
  release targeted by this draft.
- Review the prepared real-emulator screenshots with fictional data and add the
  approved release changelog. Plain captures are in the Fastlane listing; framed
  promotional images are in `assets/store/screenshots/`.
- Verify the selected upstream-signature policy against the actual CI release.
  Keep `Binaries` and the pinned `AllowedAPKSigningKeys`; do not substitute
  standard F-Droid signing if reproduction fails.
- Verify the final signed APK and real GitHub JSON asset, run the recipe on
  the actual published tag, and complete the current fdroiddata MR template.
- Verify the chosen reproducible-build signing policy before opening the merge request. A public metadata fork has already been created
  under `leodenglovescode/fdroiddata` with the maintainer's authorization.

## Files prepared locally

- `fdroid/metadata/dev.carbonpanel.yml`: draft build and update recipe.
- `fastlane/metadata/android/en-US/`: public listing text and 512px icon.
- `assets/branding/`: scalable logo assets, rendition of the maintainer's image.
- `.github/workflows/android-release.yml`: existing release workflow extended
  to publish `carbonpanel-version.json` beside successfully built APKs.
- `scripts/android_release_metadata.py`: validates release tags and derives
  the same version data for the APK and public feed.

CarbonPanel remains on GitHub. Only the metadata recipe will be submitted to
F-Droid's GitLab repository after approval. No GitLab credentials are needed
in the GitHub workflow for this update mechanism.

References:
- https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/
- https://gitlab.com/fdroid/fdroiddata/-/blob/master/CONTRIBUTING.md
- https://f-droid.org/docs/Build_Metadata_Reference/

## Current upstream template requirements

Checked against `fdroiddata/.gitlab/merge_request_templates/Default.md` on
2026-11-06. Before opening the request:

- Use title `New app: CarbonPanel` and the `New App` label.
- Include the functions, purpose, and screenshot links above.
- Use the full release commit hash in `Builds.commit`, not the tag name.
- Keep descriptions, screenshots, icon, and changelog upstream in Fastlane;
  the metadata MR should contain only `metadata/dev.carbonpanel.yml`.
- Include `AuthorName: leodenglovescode` as the public maintainer handle.
- Keep signing-policy and age-policy checklist items accurate; do not claim
  reproducibility or three months of development before verified.
- Check the fork pipeline. If GitLab requests phone or payment verification,
  leave that to F-Droid maintainers to trigger; do not provide payment details.
- No external source submodules are used. ABI splits are not configured because
  this app uses a single managed-code APK rather than per-ABI native payloads.
