#!/usr/bin/env python3
"""Capture the real Android UI from the isolated screenshot build on an emulator."""

import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "dev.carbonpanel.screenshots"


class Capture:
    def __init__(self, serial):
        if not re.fullmatch(r"emulator-[0-9]+", serial):
            raise ValueError("This script intentionally targets emulators only")
        self.serial = serial
        self.output = ROOT / "fastlane/metadata/android/en-US/images/phoneScreenshots"
        self.output.mkdir(parents=True, exist_ok=True)

    def adb(self, *args):
        return subprocess.run(
            ["adb", "-s", self.serial, *args],
            check=True,
            capture_output=True,
            timeout=25,
        ).stdout

    def nodes(self):
        self.adb("shell", "uiautomator", "dump", "/sdcard/carbonpanel-ui.xml")
        try:
            return list(
                ET.fromstring(
                    self.adb("exec-out", "cat", "/sdcard/carbonpanel-ui.xml")
                ).iter("node")
            )
        except ET.ParseError:
            # UI Automator can return an incomplete dump during app startup.
            return []

    def wait(self, text, count=1):
        for _ in range(12):
            nodes = self.nodes()
            if sum(n.get("text") == text for n in nodes) >= count:
                return nodes
            time.sleep(0.5)
        raise RuntimeError(f"Expected UI text did not appear: {text}")

    def tap(self, text, occurrence=0):
        nodes = [n for n in self.nodes() if n.get("text") == text]
        if len(nodes) <= occurrence:
            raise RuntimeError(f"Cannot find tappable text: {text}")
        bounds = list(map(int, re.findall(r"\d+", nodes[occurrence].get("bounds", ""))))
        self.adb(
            "shell",
            "input",
            "tap",
            str((bounds[0] + bounds[2]) // 2),
            str((bounds[1] + bounds[3]) // 2),
        )
        time.sleep(0.5)

    def save(self, index, label):
        time.sleep(1)
        data = self.adb("exec-out", "screencap", "-p")
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        (self.output / f"{index}.png").write_bytes(data)
        print(f"Captured {index}: {label}", flush=True)

    def capture_all(self):
        self.adb("shell", "am", "force-stop", PACKAGE)
        self.adb(
            "shell", "am", "start", "-n", f"{PACKAGE}/dev.carbonpanel.MainActivity"
        )
        self.wait("Online", count=3)
        self.save(2, "Server fleet")
        self.tap("Open")
        self.wait("CPU")
        self.save(1, "Live overview")
        self.tap("Docker")
        self.wait("paperless")
        self.save(4, "Docker containers")
        self.tap("Storage")
        self.wait("/dev/md0")
        self.save(3, "Storage and RAID")
        self.tap("More")
        self.tap("Files")
        self.wait("Getting started.md")
        self.save(5, "Read-only file browser")
        self.tap("Getting started.md")
        self.wait("Close")
        self.save(6, "Markdown preview")
        self.tap("Close")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="emulator-5580")
    args = parser.parse_args()
    Capture(args.serial).capture_all()


if __name__ == "__main__":
    main()
