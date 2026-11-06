"""Protect Android update ordering and the public F-Droid release feed."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.android_release_metadata import release_metadata

ROOT = Path(__file__).resolve().parents[2]


class ReleaseMetadataTests(unittest.TestCase):
    def test_existing_release_version_is_preserved(self):
        self.assertEqual(
            release_metadata("v1.5.0"),
            {
                "applicationId": "dev.carbonpanel",
                "versionName": "1.5.0",
                "versionCode": 10500,
                "tag": "v1.5.0",
            },
        )

    def test_order_across_minor_and_major_rollovers(self):
        tags = ["v0.0.1", "v1.5.99", "v1.6.0", "v1.99.99", "v2.0.0"]
        codes = [release_metadata(tag)["versionCode"] for tag in tags]
        self.assertEqual(codes, sorted(set(codes)))

    def test_ambiguous_and_invalid_tags_are_rejected(self):
        for tag in [
            "1.6.0",
            "v01.6.0",
            "v1.06.0",
            "v1.6.00",
            "v1.6.0-beta",
            "v1.100.0",
            "v1.0.100",
            "v0.0.0",
            "v999999.0.0",
            "v1.6.0\n",
            "v1.6.0; touch unexpected",
        ]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release_metadata(tag)

    def test_json_file_can_be_consumed_without_console_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "version.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/android_release_metadata.py"),
                    "v1.6.0",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text()), release_metadata("v1.6.0"))

    def test_invalid_release_leaves_previous_feed_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "version.json"
            output.write_text("previous release")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/android_release_metadata.py"),
                    "v1.100.0",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "previous release")


if __name__ == "__main__":
    unittest.main()
