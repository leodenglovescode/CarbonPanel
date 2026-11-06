# CarbonPanel logo

Vector rendition of the geometric C/server mark supplied by the project maintainer.
These assets are distributed under the project's MIT license.

- `carbonpanel-logo.svg`: square artwork for the README and listing icon.
- `carbonpanel-mark.svg`: transparent, tightly framed mark for application headers.
- Android adaptive and monochrome icons use the same path geometry.

Regenerate the SVGs and Android vector resources:

```sh
python3 scripts/generate_brand_assets.py
```

Export the listing PNG with ImageMagick:

```sh
convert -background none assets/branding/carbonpanel-logo.svg -resize 512x512 -depth 8 -strip PNG32:fastlane/metadata/android/en-US/images/icon.png
```

The supplied design is represented as flat vector geometry, without the raster's
subtle texture. Launcher foreground padding keeps the mark within Android icon masks.
