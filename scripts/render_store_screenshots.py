#!/usr/bin/env python3
"""Frame actual Android captures with concise, factual feature descriptions."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "fastlane/metadata/android/en-US/images/phoneScreenshots"
OUT = ROOT / "assets/store/screenshots"
FONT = Path("/usr/share/fonts/truetype/dejavu")
SCENES = [
    (
        "overview",
        "Server monitoring",
        "View CPU, memory, disk usage",
        "and network activity.",
    ),
    (
        "servers",
        "Multiple servers",
        "Save several servers and check",
        "their status before opening one.",
    ),
    (
        "storage",
        "Storage and RAID",
        "View disk capacity, RAID status",
        "and available SMART readings.",
    ),
    (
        "containers",
        "Docker containers",
        "Check resource usage and start,",
        "stop or restart containers.",
    ),
    (
        "files",
        "Read-only file browser",
        "Browse and download files.",
        "No editing or deletion controls.",
    ),
    (
        "preview",
        "File previews",
        "Open Markdown, text, code, images",
        "and supported videos in the app.",
    ),
]


def font(size, bold=False):
    return ImageFont.truetype(
        str(FONT / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    images = []
    for index, (slug, title, line1, line2) in enumerate(SCENES, 1):
        with Image.open(RAW / f"{index}.png") as raw:
            source = raw.convert("RGB")
        if source.size != (1080, 2400):
            raise ValueError(f"Expected 1080×2400 capture: {index}, got {source.size}")
        canvas = Image.new("RGB", (1440, 2880), "#080E0B")
        draw = ImageDraw.Draw(canvas)
        draw.line((112, 164, 184, 164), fill="#00FF88", width=6)
        draw.text((108, 220), title, font=font(84, True), fill="#EEF6F0")
        draw.text((112, 358), line1, font=font(38), fill="#B8C8BE")
        draw.text((112, 414), line2, font=font(38), fill="#B8C8BE")
        # A neutral device surround; the actual UI content is unchanged.
        draw.rounded_rectangle(
            (216, 572, 1224, 2768),
            radius=66,
            fill="#17231C",
            outline="#384B3E",
            width=3,
        )
        screenshot = source.resize((972, 2160), Image.Resampling.LANCZOS)
        mask = Image.new("L", screenshot.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 971, 2159), radius=48, fill=255)
        canvas.paste(screenshot, (234, 590), mask)
        footer = "Screenshots use demo data"
        width = draw.textlength(footer, font=font(22))
        draw.text(((1440 - width) / 2, 2810), footer, font=font(22), fill="#8BA393")
        canvas.save(OUT / f"{index:02}-{slug}.png", optimize=True)
        images.append(canvas)
    sheet = Image.new("RGB", (1440, 1920), "#080E0B")
    for index, image in enumerate(images):
        sheet.paste(
            image.resize((480, 960), Image.Resampling.LANCZOS),
            ((index % 3) * 480, (index // 3) * 960),
        )
    sheet.save(OUT / "contact-sheet.png", optimize=True)
    print("Rendered six feature images and a contact sheet from actual app captures.")


if __name__ == "__main__":
    main()
