# Android promotional screenshots

Six feature cards combine actual Android app captures with a simple phone surround, a feature name, and a factual description. `screenshots/contact-sheet.png` previews the
set; the numbered PNGs are full-size 1440×2880 artwork. Plain 1080×2400 captures
live in `fastlane/metadata/android/en-US/images/phoneScreenshots/` for F-Droid.
All names, metrics, documents and file listings are fictional demo data.

## Reproduce

Use an Android API 35 emulator at 1080×2400, density 420, dark mode and gesture
navigation. The capture script intentionally rejects physical device serials.
The screenshot APK uses a separate application ID (`dev.carbonpanel.screenshots`)
and locally pinned HTTPS fixture servers. It never connects to your NAS or uses
real account credentials. Fixtures and mock server dependencies belong only to
the `screenshot` build variant, not the release APK.

```sh
python3 scripts/generate_screenshot_fixtures.py
cd android
./gradlew :app:assembleScreenshot
cd ..
adb -s emulator-5580 install -r android/app/build/outputs/apk/screenshot/app-screenshot.apk
python3 scripts/capture_android_screenshots.py --serial emulator-5580
python3 scripts/render_store_screenshots.py
```

Rendering needs Python Pillow and the system DejaVu fonts
(`/usr/share/fonts/truetype/dejavu`). The renderer scales and rounds the captures
without changing the app content. No AI-generated interface elements are used.
The fixture application rejects mutations; container action buttons are the real
UI but cannot change anything in this build.

These are local listing drafts, not evidence of F-Droid acceptance or publication.
