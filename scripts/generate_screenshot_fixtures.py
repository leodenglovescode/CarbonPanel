#!/usr/bin/env python3
"""Deterministic fictional data for the screenshot-only Android application."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "android/app/src/screenshot/assets/demo"
TS = datetime(2026, 11, 6, 9, 41, tzinfo=timezone.utc).timestamp()


def write(name, data):
    (ROOT / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for index, (name, cpu, memory, uptime) in enumerate(
        [
            ("atlas", 18.4, 42.2, 2953200),
            ("harbor", 8.6, 26.4, 1584000),
            ("forge", 36.8, 57.1, 446400),
        ]
    ):
        write(
            f"metrics-{index}",
            {
                "ts": TS,
                "cpu": {
                    "aggregate": cpu,
                    "per_core": [12, 24, 18, 9, 31, 14, 22, 17],
                    "load_avg": [1.24, 1.08, 0.96],
                    "frequency_mhz": 3800,
                    "cpu_name": "AMD Ryzen 7 5700G",
                    "temps": [
                        {"sensor": "k10temp", "label": "CPU package", "temp_c": 46.0}
                    ],
                },
                "memory": {
                    "total_mb": 16384,
                    "used_mb": round(16384 * memory / 100, 1),
                    "free_mb": round(16384 * (100 - memory) / 100, 1),
                    "percent": memory,
                },
                "network": [
                    {
                        "interface": "eth0",
                        "rx_mb_s": 12.8,
                        "tx_mb_s": 3.4,
                        "rx_total_mb": 845312,
                        "tx_total_mb": 213504,
                    }
                ],
                "system": {
                    "hostname": name,
                    "uptime_seconds": uptime,
                    "boot_time_ts": TS - uptime,
                    "timezone": "UTC",
                    "utc_offset_seconds": 0,
                    "docker_installed": True,
                },
            },
        )
    write(
        "history",
        [
            {
                "ts": TS - (89 - i) * 20,
                "cpu": round(20 + 7 * math.sin(i * 0.14) + 3 * math.sin(i * 0.43), 2),
                "mem": round(41.2 + 1.5 * math.sin(i * 0.035), 2),
            }
            for i in range(90)
        ],
    )
    write(
        "disks",
        [
            {
                "device": "/dev/md0",
                "physical_device": "/dev/md0",
                "mountpoint": "/srv/storage",
                "fstype": "xfs",
                "opts": "rw",
                "total_gb": 7450,
                "used_gb": 3427,
                "free_gb": 4023,
                "usage_percent": 46,
                "read_mb_s": 24.8,
                "write_mb_s": 8.2,
                "bus_type": "SATA",
                "smart": None,
            },
            {
                "device": "/dev/nvme0n1p2",
                "physical_device": "/dev/nvme0n1",
                "mountpoint": "/",
                "fstype": "ext4",
                "opts": "rw",
                "total_gb": 476.9,
                "used_gb": 128.4,
                "free_gb": 348.5,
                "usage_percent": 26.9,
                "read_mb_s": 2.3,
                "write_mb_s": 0.8,
                "bus_type": "NVMe",
                "smart": {
                    "model": "System SSD",
                    "health": "PASSED",
                    "temperature_c": 38,
                    "power_on_hours": 3120,
                },
            },
        ],
    )
    write(
        "nas",
        {
            "raid": {
                "available": True,
                "arrays": [
                    {
                        "device": "/dev/md0",
                        "level": "raid1",
                        "state": "clean",
                        "size_bytes": 7999376588800,
                        "raid_disks": 2,
                        "degraded": 0,
                        "sync_action": "idle",
                        "members": [
                            {"device": "/dev/sda1", "state": "in_sync", "slot": "0"},
                            {"device": "/dev/sdb1", "state": "in_sync", "slot": "1"},
                        ],
                    }
                ],
                "errors": [],
            }
        },
    )
    write(
        "containers",
        [
            {
                "id": name,
                "name": name,
                "image": image,
                "status": "Up 12 days",
                "state": "running",
                "ports": ports,
                "cpu_percent": cpu,
                "mem_usage_mb": memory,
                "mem_limit_mb": 16384,
                "mem_percent": round(memory / 16384 * 100, 1),
            }
            for name, image, ports, cpu, memory in [
                (
                    "paperless",
                    "ghcr.io/paperless-ngx/paperless-ngx:latest",
                    "8000 → 8000",
                    2.4,
                    412,
                ),
                ("nextcloud", "nextcloud:stable", "8080 → 80", 1.8, 286),
                ("postgres", "postgres:17-alpine", "5432", 0.6, 128),
                ("redis", "redis:7-alpine", "6379", 0.2, 24),
            ]
        ],
    )
    write(
        "services",
        [
            {
                "service_name": name + ".service",
                "description": description,
                "load_state": "loaded",
                "active_state": "active",
                "sub_state": "running",
                "uptime": "12 days",
                "pid": 1200 + index,
                "unit_file_state": "enabled",
                "autostart_enabled": True,
                "starred": index < 2,
            }
            for index, (name, description) in enumerate(
                [
                    ("nginx", "Web server and reverse proxy"),
                    ("docker", "Container runtime"),
                    ("carbonpanel-backend", "CarbonPanel monitoring API"),
                    ("ssh", "OpenSSH server"),
                    ("smartd", "Disk health monitoring"),
                ]
            )
        ],
    )
    entries = [
        {
            "name": name,
            "path": "/" + name,
            "directory": directory,
            "kind": kind,
            "size": size,
            "modified": TS - 86400,
        }
        for name, directory, kind, size in [
            ("Documents", True, "directory", None),
            ("Media", True, "directory", None),
            ("Projects", True, "directory", None),
            ("Getting started.md", False, "markdown", 2846),
            ("backup-plan.py", False, "text", 4832),
            ("storage-report.csv", False, "text", 24576),
            ("network-map.png", False, "image", 368640),
            ("server-tour.mp4", False, "video", 25165824),
        ]
    ]
    write(
        "files",
        {
            "path": "/",
            "parent": None,
            "entries": entries,
            "total": len(entries),
            "offset": 0,
            "has_more": False,
        },
    )
    write("backgrounds", {"targets": {}, "surfaceTransparency": 0})
    write("preferences", {"prefs": {}})
    write(
        "user",
        {
            "id": "demo",
            "username": "demo",
            "totp_enabled": True,
            "onboarding_completed": True,
        },
    )
    (ROOT / "preview.html").write_text(
        """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#101412;color:#e2ece6;font:16px/1.65 sans-serif;padding:22px}h1{font-size:26px}h2{font-size:19px;color:#00ff88}code{background:#1c2521;padding:3px 7px;border-radius:4px}li{margin:10px 0}small{color:#a0aaa4}</style></head><body><small>DOCUMENTATION · DEMO</small><h1>Your homelab, organized.</h1><p>A small runbook for keeping the essentials in one place.</p><h2>Daily checks</h2><ul><li>Review server health and storage usage.</li><li>Check that scheduled backups completed.</li><li>Keep a copy of your recovery instructions.</li></ul><h2>Storage</h2><p>Shared files live in <code>/srv/storage</code>. View files here or download a copy when you need it.</p><p><small>This is fictional sample content for CarbonPanel screenshots.</small></p></body></html>"""
    )


if __name__ == "__main__":
    main()
