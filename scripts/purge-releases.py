#!/usr/bin/env python3
"""Purge only identified, inactive CarbonPanel releases. Caller holds update.lock."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Release:
    path: Path
    device: int
    inode: int


def is_release(path: Path) -> bool:
    """Accept installer names with validated deployment metadata or a build marker."""
    if not re.fullmatch(r"[0-9]{14}-[a-zA-Z0-9._-]+", path.name):
        return False
    for name in (".carbonpanel-release.json", ".carbonpanel-build.json"):
        metadata = path / name
        if metadata.is_symlink() or not metadata.is_file():
            continue
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if (
            isinstance(data, dict)
            and all(isinstance(data.get(key), str) and data[key]
                    for key in ("repo_url", "version", "commit", "installed_at"))
            and re.fullmatch(r"[0-9a-f]{40,64}", data["commit"])
            and data.get("source_type") in ("branch", "tag")
        ):
            return True
    return False


def protected_releases(root: Path, releases: Path) -> set[Path]:
    protected: set[Path] = set()
    for name in ("current", "previous"):
        link = root / name
        if name == "previous" and not link.exists() and not link.is_symlink():
            continue
        if not link.is_symlink():
            raise ValueError(f"Refusing purge: {link} must be a release symlink")
        target = link.resolve(strict=True)
        if target.parent != releases or not target.is_dir():
            raise ValueError(f"Refusing purge: {link} points outside the release layout")
        protected.add(target)
    return protected


def mount_points() -> set[Path]:
    # ismount() alone misses bind mounts on the same filesystem. This installer
    # targets Linux; if mount information cannot be read, fail closed.
    return {
        Path(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), line.split()[4]))
        for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    }


def plan_purge(root: Path) -> tuple[Path, set[Path], list[Release]]:
    root = root.resolve(strict=True)
    releases = root / "releases"
    if releases.is_symlink() or not releases.is_dir():
        raise ValueError("Refusing purge: releases must be a real directory")
    protected = protected_releases(root, releases)
    mounts = mount_points()
    candidates: list[Release] = []
    for path in sorted(releases.iterdir()):
        info = path.lstat()
        if path in protected:
            continue
        if not stat.S_ISDIR(info.st_mode) or not is_release(path):
            print(f"Skipping unrecognized entry: {path}", file=sys.stderr)
            continue
        # Never descend into mounted data, including nested bind mounts.
        if any(mount.is_relative_to(path) for mount in mounts):
            raise ValueError(f"Refusing purge: mounted directory inside {path}")
        candidates.append(Release(path, info.st_dev, info.st_ino))
    return releases, protected, candidates


def purge_releases(root: Path, *, dry_run: bool = False) -> int:
    releases, protected, candidates = plan_purge(root)
    if not dry_run and not shutil.rmtree.avoids_symlink_attacks:
        raise RuntimeError("Safe directory removal is unavailable on this platform")
    # Anchor removals to the validated releases directory, never a resolved
    # candidate symlink. rmtree also refuses symlink replacements internally.
    descriptor = os.open(releases, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for release in candidates:
            if protected_releases(releases.parent, releases) != protected:
                raise RuntimeError("Release links changed during purge; stopped")
            info = os.stat(release.path.name, dir_fd=descriptor, follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (release.device, release.inode):
                raise RuntimeError(f"Release changed during purge: {release.path}")
            if dry_run:
                print(f"Would remove: {release.path}")
            else:
                shutil.rmtree(release.path.name, dir_fd=descriptor)
                print(f"Removed: {release.path}")
    finally:
        os.close(descriptor)
    print(f"{'Would remove' if dry_run else 'Removed'} {len(candidates)} obsolete release(s)")
    return len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("install_root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        purge_releases(args.install_root, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Purge failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
