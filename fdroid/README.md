# F-Droid submission preparation

Submission preparation. A public metadata fork exists at
https://gitlab.com/leodenglovescode/fdroiddata. No merge request or new release
has been published. CarbonPanel source remains on GitHub.

## Updates after inclusion

The existing Android release workflow creates `carbonpanel-version.json` from
the exact release tag and publishes it alongside the APK **only after a successful
build, signature verification, and a clean unsigned rebuild/signature-copy check**. Backend-only tags remain skipped.

The draft `metadata/dev.carbonpanel.yml` uses F-Droid's `UpdateCheckMode: HTTP`
to read this asset at GitHub's `releases/latest/download` URL. `AutoUpdateMode:
Version v%v` selects that version's Git tag. Its reusable prebuild writes
`$$VERSION$$` and `$$VERCODE$$` into Gradle properties, so future build entries
do not retain the first release's version. This uses F-Droid's update machinery;
no GitLab token or cross-repository publishing bot is needed in GitHub Actions.

Prerequisite: the first approved Android release must contain the metadata asset.
It is not present on v1.5.0. The update URL cannot work until such a release exists.
F-Droid controls its build checks, review, and publication schedule.

## Building unsigned

```sh
cd android
./gradlew :app:assembleRelease -PcarbonUnsigned=true -PcarbonVersionName=1.6.0 -PcarbonVersionCode=10600
```

`carbonUnsigned=true` avoids reading release-signing environment variables and
produces an unsigned APK. GitHub builds keep their existing signing configuration.
Encrypted Google Play dependency metadata is disabled for all builds.

## Submission approval checklist

1. Review `docs/fdroid-submission-draft.md`, listing copy, and icon.
2. Review the six real-emulator screenshots in `fastlane/metadata/android/en-US/images/phoneScreenshots/`
   and the promotional artwork in `assets/store/screenshots/`. All server data is fictional.
3. Publish and verify the first release carrying these changes (`v1.6.0` / `10600`).
4. Preserve the GitHub signing identity through reproducible-build verification,
   as selected by the maintainer. `Binaries` points to the matching GitHub release
   APK and `AllowedAPKSigningKeys` pins its public certificate fingerprint.
   A mismatch must block publication; do not fall back to a different signing key.
5. After approval, publish the source and the first tag carrying the artwork,
   packaging changes, and JSON feed. Verify the signed APK has no dependency block.
6. Copy `metadata/dev.carbonpanel.yml` into a branch of an approved GitLab fdroiddata
   fork, run F-Droid metadata/build checks on the actual tag, and show the complete
   request for approval before opening it against fdroid/fdroiddata. The current template requires
   a full source commit hash and keeps listing descriptions in upstream Fastlane.

Local parsing, simulated update checks, source scans, and unsigned local builds
are preparation evidence, not acceptance or a build on F-Droid infrastructure.

References:
- https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/
- https://f-droid.org/docs/Build_Metadata_Reference/#AutoUpdateMode

## Local validation (2026-11-06)

- Android: 26 unit tests passed; unsigned release builds successfully with the
  proposed `1.6.0` / `10600` properties.
- Recipe preparation: a temporary source export also builds after F-Droid's
  signing-config cleanup and the exact recipe prebuild.
- Release metadata: 5 unit tests passed; the actual workflow version step was
  executed in an isolated directory and produced matching APK version properties
  and JSON data. Workflow YAML and embedded shell syntax passed; tag-only release
  triggers and the Android-change check are preserved.
- F-Droid: metadata parsed and linted using upstream category names; source scan
  returned 0 problems and 0 warnings; the unsigned APK scan passed.
- Update simulation: F-Droid generated `v1.6.1` / `10601` and `v2.0.0` / `20000`
  build entries from simulated feed data, with updated Gradle version properties.
  No requests were posted and no Git commits were made by that simulation.
- Frontend: production build, TypeScript checking, and lint of changed components passed.
- Artwork: SVG/Android vector generation is repeatable; the listing icon is
  512×512, 8-bit RGBA PNG, with metadata stripped.

- Screenshot verification: release build and 26 Android unit tests passed after
  adding the isolated fixture variant. The release APK contains no demo assets,
  fixture Application, or MockWebServer classes. Six plain captures and six
  promotional cards are prepared; see `assets/store/README.md`.

The actual next tag, public JSON URL, final signed APK, and F-Droid infrastructure
build remain to be verified after approval and release. Local independent builds passed signature copying with a test key. Verification
against the published CI-signed APK and F-Droid infrastructure is still required.

## Reproducibility verification

Two fresh Android source copies were built without task/build caches at different
absolute paths: one unsigned, one signed only with the local debug test key.
`apksigcopier 1.1.1` copied public signatures from the latter onto the former;
`apksigner verify` succeeded and `cmp` found the APKs byte-identical. Private
release-signing material was not accessed. This tests deterministic packaging,
not F-Droid's independent build environment.

The GitHub workflow repeats signature-copy verification after a clean unsigned
rebuild and before releasing any APK or version JSON. The source tag supplies
both version properties. F-Droid must independently reproduce that release before
publishing it with the pinned GitHub signature. See
https://f-droid.org/docs/Reproducible_Builds/.
