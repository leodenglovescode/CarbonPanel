# Android reproducibility verification — v1.6.0

Verified on 2026-11-06 for source commit
`552ba971d1988dde3dded060db09bc2c7a2afe95`.

## Result

The signed GitHub release APK was reproduced byte for byte by an independent
local build of the tagged source using F-Droid's signing-configuration cleanup
and the recipe's Gradle version properties. Only public APK signatures were
copied; private release-signing material was not accessed for verification.

- Release: https://github.com/leodenglovescode/CarbonPanel/releases/tag/v1.6.0
- CI verification: https://github.com/leodenglovescode/CarbonPanel/actions/runs/42177389382
- APK SHA-256: `61858870a1daf03fed1fe841d9b479ff0e5bab8c0f3273528f45b69467e90969`
- Certificate SHA-256: `f06b0403ff6784ff9ec32e6d0f96468ed044795847b8f29a537a6e26c08b20fd`

## Checks performed

1. Built two fresh source copies at different paths without Gradle task/build
   caches, one unsigned and one signed with the ordinary local debug test key.
2. Used `apksigcopier 1.1.1` to copy public signatures, verified with Android
   build-tools 36.1.0 `apksigner`, and compared the complete APKs with `cmp`.
3. Built the exact published tag independently after F-Droid signing-config
   cleanup and recipe version properties. Local build used OpenJDK 21;
   upstream GitHub CI used Temurin 17. Both used build-tools 36.1.0.
4. Downloaded the CI-signed v1.6.0 APK, copied its public signatures onto the
   recipe rebuild, verified the signature, and compared the full APK bytes.
   SHA-256 hashes matched exactly. The certificate also matches v1.5.0.
5. F-Droid's binary scanner passed. Independent APK signing-block inspection
   confirmed the encrypted dependency metadata block is absent. The release
   version JSON reports 1.6.0 / 10600 and the correct tag/application ID.
6. The release workflow now performs a fresh unsigned rebuild and signature-copy
   comparison before publishing APKs or the version feed.

## F-Droid submission

MR: https://gitlab.com/fdroid/fdroiddata/-/merge_requests/56044

The one-file recipe pins the full source commit and public signing certificate,
with `Binaries` pointing to the matching GitHub release. It does not permit a
fallback to F-Droid signing when verification fails. The fdroiddata recipe CI build has now also reproduced the release successfully:
https://gitlab.com/leodenglovescode/fdroiddata/-/jobs/17797836424
Its log reports successful upstream APK verification. Final repository acceptance
and publication are still controlled by F-Droid maintainers.

The account-verification restriction was cleared by the maintainer. The initial
CI run then exposed metadata formatting and APK-discovery issues, corrected in
recipe commit `49867f07054b416553ebd2211c4af4a17fec18ac`. The recipe explicitly
selects the app module's APK and uses CI's YAML formatting. The corrected build
and reproducibility check passed, and all nine pipeline jobs are green:
https://gitlab.com/leodenglovescode/fdroiddata/-/pipelines/3035477195

The APK report flags network and camera permissions as minor review items: they
are needed for server connections and QR pairing. Remaining permission/signing/
ABI entries are informational. CI tooling also emits environment warnings
(outdated API lookup data, config-file mode, Python dependency syntax), which did
not fail checks and are not app build failures.

The MR also discloses the Android development start date (2026-08-08) and asks
that inclusion wait until the three-month point (2026-11-08); no age exception
is claimed.

References:
- https://f-droid.org/docs/Reproducible_Builds/
- https://f-droid.org/docs/Inclusion_Policy/
