"""Read-only browsing with the backend's OS identity; no privileged helpers."""

from __future__ import annotations

import html
import os
import re
import stat
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

MAX_TEXT_BYTES = 1024 * 1024
MAX_ENTRIES = 10_000
MEDIA = {
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".png": ("image", "image/png"),
    ".gif": ("image", "image/gif"),
    ".webp": ("image", "image/webp"),
    ".avif": ("image", "image/avif"),
    ".bmp": ("image", "image/bmp"),
    ".ico": ("image", "image/x-icon"),
    ".mp4": ("video", "video/mp4"),
    ".m4v": ("video", "video/mp4"),
    ".webm": ("video", "video/webm"),
    ".ogv": ("video", "video/ogg"),
    ".mov": ("video", "video/quicktime"),
    ".mp3": ("audio", "audio/mpeg"),
    ".wav": ("audio", "audio/wav"),
    ".ogg": ("audio", "audio/ogg"),
    ".m4a": ("audio", "audio/mp4"),
}
TEXT_EXTENSIONS = set(
    (
        "txt md markdown py js ts tsx jsx vue json jsonl yaml yml toml ini cfg conf sh bash "
        "zsh fish css scss html htm xml svg csv tsv log rst sql c h cpp hpp rs go java kt "
        "kts rb php swift dockerfile env gitignore properties service"
    ).split()
)
BLOCKED = ("/proc", "/sys", "/dev")


class BrowserError(Exception):
    def __init__(self, status: int, detail: str):
        self.status, self.detail = status, detail
        super().__init__(detail)


def canonical(path: str) -> Path:
    if not path.startswith("/") or "\x00" in path:
        raise BrowserError(400, "An absolute path is required")
    try:
        result = Path(path).resolve(strict=True)
    except (ValueError, RuntimeError, OSError) as exc:
        raise map_error(exc) from exc
    if any(str(result) == root or str(result).startswith(root + "/") for root in BLOCKED):
        raise BrowserError(403, "Virtual devices and kernel files cannot be browsed")
    return result


def map_error(exc: Exception) -> BrowserError:
    if isinstance(exc, PermissionError):
        return BrowserError(403, "The CarbonPanel service account cannot read this path")
    if isinstance(exc, FileNotFoundError):
        return BrowserError(404, "This path no longer exists")
    if isinstance(exc, NotADirectoryError):
        return BrowserError(400, "This path is not a directory")
    return BrowserError(400, "This path cannot be opened")


def open_path(path: str, directory: bool = False):
    resolved = canonical(path)
    # Walk canonical components without following links. The opened descriptor
    # remains tied to this inode if a path is renamed while it is streamed.
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        parts = resolved.parts[1:]
        for index, component in enumerate(parts):
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
            if index < len(parts) - 1 or directory:
                flags |= os.O_DIRECTORY
            next_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        info = os.fstat(descriptor)
        expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if not expected:
            raise BrowserError(400, "Only regular files and directories are supported")
        return resolved, descriptor, info
    except BrowserError:
        os.close(descriptor)
        raise
    except OSError as exc:
        os.close(descriptor)
        raise map_error(exc) from exc


def kind(path: str):
    suffix = Path(path).suffix.lower()
    if suffix in MEDIA:
        return MEDIA[suffix]
    if suffix.lstrip(".") in TEXT_EXTENSIONS or Path(path).name.lower() in (
        "makefile",
        "dockerfile",
        "license",
        "readme",
        ".gitignore",
        ".env",
    ):
        return ("markdown" if suffix in (".md", ".markdown") else "text", "text/plain")
    return "file", "application/octet-stream"


def list_directory(
    path: str,
    offset: int = 0,
    limit: int = 200,
    search: str = "",
    sort: str = "name",
    descending: bool = False,
    show_hidden: bool = True,
):
    resolved, descriptor, _ = open_path(path, directory=True)
    entries = []
    try:
        with os.scandir(descriptor) as iterator:
            for entry in iterator:
                if len(entries) >= MAX_ENTRIES:
                    raise BrowserError(
                        413,
                        "This directory has more than 10,000 entries. Open a more specific path.",
                    )
                try:
                    info = entry.stat(follow_symlinks=False)
                    is_link = stat.S_ISLNK(info.st_mode)
                    if is_link:
                        child = canonical(str(resolved / entry.name))
                        info = child.stat()
                    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                        continue
                    directory = stat.S_ISDIR(info.st_mode)
                    entries.append(
                        {
                            "name": entry.name,
                            "path": str(resolved / entry.name),
                            "directory": directory,
                            "symlink": is_link,
                            "size": info.st_size if not directory else None,
                            "modified": info.st_mtime,
                            "kind": "directory" if directory else kind(entry.name)[0],
                        }
                    )
                except (OSError, BrowserError):
                    continue
    except OSError as exc:
        raise map_error(exc) from exc
    finally:
        os.close(descriptor)
    needle = search.casefold()
    entries = [
        e
        for e in entries
        if (show_hidden or not e["name"].startswith(".")) and needle in e["name"].casefold()
    ]

    def order(entry):
        name = (entry["name"].casefold(), entry["name"])
        if sort == "modified":
            return (entry["modified"], *name)
        if sort == "size":
            return (entry["size"] or 0, *name)
        if sort == "kind":
            return (entry["kind"], *name)
        return name

    entries.sort(key=order, reverse=descending)
    entries.sort(key=lambda e: not e["directory"])

    return {
        "path": str(resolved),
        "parent": str(resolved.parent) if resolved != Path("/") else None,
        "entries": entries[offset : offset + limit],
        "total": len(entries),
        "offset": offset,
        "has_more": offset + limit < len(entries),
    }


def byte_range(header: str | None, size: int):
    if not header:
        return 0, size - 1, False
    if len(header) > 100:
        raise BrowserError(416, "Requested range is not available")
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()) or size == 0:
        raise BrowserError(416, "Requested range is not available")
    first, last = match.groups()
    if not first:
        length = int(last)
        if length <= 0:
            raise BrowserError(416, "Requested range is not available")
        start, end = max(0, size - length), size - 1
    else:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        raise BrowserError(416, "Requested range is not available")
    return start, end, True


def rendered_text(path: str):
    resolved, descriptor, info = open_path(path)
    with os.fdopen(descriptor, "rb") as source:
        raw = source.read(MAX_TEXT_BYTES + 1)
    if len(raw) > MAX_TEXT_BYTES:
        raise BrowserError(
            413, "Text previews are limited to 1 MiB. Download this file to view it in full."
        )
    if b"\x00" in raw and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise BrowserError(415, "This binary file is available for download only")
    try:
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BrowserError(
            415, "This file is not UTF-8 or UTF-16 text. Download it to view locally."
        ) from exc
    formatter = HtmlFormatter(cssclass="code", style="github-dark")

    def code_block(code, language, _attrs):
        from pygments.lexers import get_lexer_by_name

        try:
            lexer = get_lexer_by_name(language)
        except ClassNotFound:
            lexer = TextLexer()
        return highlight(code, lexer, formatter)

    if resolved.suffix.lower() in (".md", ".markdown"):
        renderer = MarkdownIt("commonmark", {"html": False, "highlight": code_block}).enable(
            ["table", "strikethrough"]
        )
        # Documents cannot initiate network requests or pull in private image URLs.
        renderer.disable("image")
        body = renderer.render(text)
    else:
        try:
            lexer = get_lexer_for_filename(resolved.name)
        except ClassNotFound:
            lexer = TextLexer()
        body = highlight(text, lexer, formatter)
    title = html.escape(resolved.name)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:dark light}}
body{{margin:0;
padding:20px;
background:#101412;
color:#e0e6e2;
font:14px/1.7 system-ui,sans-serif;
overflow-wrap:anywhere}}
pre{{overflow:auto;
padding:14px;
border:1px solid #334139;
border-radius:6px;
white-space:pre;
tab-size:4}}
code{{font-family:ui-monospace,monospace}}
a{{color:#69c99a}}
table{{border-collapse:collapse;
display:block;
overflow:auto}}
td,th{{padding:8px 12px;
border:1px solid #334139}}
blockquote{{border-left:3px solid #69c99a;
padding-left:16px;
margin-left:0}}
h1,h2,h3{{line-height:1.3}}
{formatter.get_style_defs(".code")}
</style></head><body>{body}</body></html>"""
