# File browser interaction design

The web panel and Android app use the same read-only browsing flow.

- Open a folder in one click/tap; open a file to preview it. Download is a separate,
  explicitly labeled action, so opening a document does not unexpectedly save it.
- Use clickable folder breadcrumbs and Parent folder. Web folder paths are in
  the URL, so browser Back/Forward and direct links work. Android system Back
  returns to the parent folder before leaving Files.
- Switch between list and adaptive grid views with dedicated controls. The view
  choice survives restart. Grids use folder/file icons and lazy image previews;
  images above 8 MiB use icons until explicitly opened, avoiding large automatic
  transfers from a NAS. File access remains authenticated.
- Search names and sort the whole current directory before paginating. Search
  does not recurse into subfolders. Folders remain first in every sort mode.
  Search is debounced, and changing its options resets pagination.
- Short Android windows use a compact toolbar with expandable search so file
  content remains reachable in landscape.
- The web path bar is always visible and editable, with explicit missing-path
  errors. Android offers Go to folder in the folder menu. Web locations use
  mounted paths from live metrics, excluding Snap and virtual system mounts.
- Folder navigation keeps the current listing visible while the next request
  completes, without skeletons or a page fade. A text status reports the request.
  Preview loading follows image/document events. Web video/audio buffering uses
  media events; Android retains the WebView's native playback/buffering controls
  with JavaScript and external resources disabled.
- Web downloads validate access with HEAD, then use the browser download manager
  for transfer progress. The panel reports handoff, not false download completion.
- Android uses the native save-location picker and streams directly to the chosen
  destination, with transferred bytes, progress when the response length is known,
  cancellation, and completion/failure feedback. Activity-owned transfer state
  survives page changes and device rotation while the app process is alive.
  Streaming requests have no total-duration deadline and a 30-second inactivity
  timeout; process-death recovery/resume is not implemented. A canceled transfer may leave a
  partial local file; no server file is changed.
- Empty folders, no matches, unsupported previews, and permission/network failures
  have distinct states and appropriate retry, clear-search, or download actions.
- Controls have accessible names and focus indicators. Web dialog focus/Escape
  behavior is preserved, narrow layouts are checked, and reduced-motion settings
  disable decorative web loading animations.

The existing 10,000-entry directory ceiling and 1 MiB text-preview limit remain.
Deploy the updated backend with the clients to enable directory-wide search,
sorting and hidden-file filtering; older servers do not implement those queries.

## Guidance used

- Nielsen Norman Group, breadcrumbs: show the current location and ancestors,
  with usable mobile controls rather than tiny wrapping paths.
  https://www.nngroup.com/articles/breadcrumbs/
- Material progress indicators: use indeterminate indicators for unknown waits
  and determinate indicators only when actual progress can be measured.
  https://developer.android.com/develop/ui/compose/components/progress
- Material usage guidance: indicators communicate real operation status and
  available actions consistently.
  https://m2.material.io/components/progress-indicators

## Verification

Backend regression tests cover authenticated read-only access, path/stream safety,
search before pagination, hidden files, and size/date ordering with folders first.
Browser checks exercise list/grid, folder history, search/sort queries, previews,
actual browser downloads, permission failures, and narrow-screen overflow.
Native emulator checks exercise the isolated demo application; production builds
exclude demo fixtures and never use a real NAS account for these checks.

Validation on 2026-11-11: 10 backend file-browser tests and 26 Android unit tests
passed; frontend production/type build and changed-file ESLint passed; debug,
screenshot and unsigned release APKs built. Browser interaction checks passed
with fictional data and network delays. Native emulator checks passed folder
navigation, list/grid, search, previews, the save picker, a streamed transfer
longer than 15 seconds, leaving/reopening Files during transfer, device rotation,
and cancellation with persistent feedback. Demo assets are absent from the
release APK. No physical phone or real NAS was used for these checks.
