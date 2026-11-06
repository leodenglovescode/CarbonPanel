#!/usr/bin/env python3
"""Produce the public F-Droid update feed from an Android release tag."""

import argparse
import json
import re
from pathlib import Path

TAG_PATTERN = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def release_metadata(tag: str) -> dict:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError(
            "Release tag must be vMAJOR.MINOR.PATCH without leading zeroes"
        )
    major, minor, patch = map(int, match.groups())
    if minor > 99 or patch > 99:
        raise ValueError(
            "Minor and patch must be at most 99 to keep versionCode unique"
        )
    code = major * 10000 + minor * 100 + patch
    if not 1 <= code <= 2147483647:
        raise ValueError("versionCode must be a positive signed 32-bit integer")
    return {
        "applicationId": "dev.carbonpanel",
        "versionName": f"{major}.{minor}.{patch}",
        "versionCode": code,
        "tag": tag,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        text = json.dumps(release_metadata(args.tag), indent=2) + "\n"
    except ValueError as error:
        parser.error(str(error))
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
