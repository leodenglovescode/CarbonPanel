#!/usr/bin/env python3
"""CarbonPanel kiosk client for a Pi driving a small SPI framebuffer (e.g.
/dev/fb1 from the fbtft/ili9486 driver). No X11, no browser — draws frames
with Pillow straight into the fb device node and reads the resistive
touchscreen straight off its evdev node. Targets the fb's native refresh
budget (~30fps) instead of a browser's DOM/animation overhead.

Setup on the Pi:
    cd pi-kiosk
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    cp config.example.json config.json   # fill in base_url/username/password
    .venv/bin/python kiosk.py config.json

Run `python3 kiosk.py --selftest` to sanity-check the framebuffer pixel
packing without touching real hardware.
"""
import asyncio
import json
import selectors
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FB_DEVICE = "/dev/fb1"
FB_W, FB_H = 480, 320
# Some fbtft panels want R/B swapped relative to standard RGB565 — if colors
# come out wrong (red/blue swapped) on the real screen, flip this to True.
FB_SWAP_RB = False

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_PATH_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

BG = (10, 12, 11)
FG = (230, 240, 235)
FG_MUTED = (130, 145, 138)
ACCENT = (0, 255, 136)
WARNING = (255, 180, 40)
DANGER = (255, 70, 70)
BORDER = (40, 48, 44)

TAB_H = 34
PAGES = ["overview", "disks"]


def font(size, bold=False):
    path = FONT_PATH if bold else FONT_PATH_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def pack_fb_bytes(img: Image.Image) -> bytes:
    """RGB888 -> little-endian RGB565, vectorized (pure-Python per-pixel
    packing can't keep up with 480x320 @ 30fps)."""
    arr = np.asarray(img.convert("RGB"), dtype=np.uint16)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    if FB_SWAP_RB:
        r, b = b, r
    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return rgb565.astype("<u2").tobytes()


def write_frame(img: Image.Image, fb=None):
    data = pack_fb_bytes(img)
    if fb is None:
        with open(FB_DEVICE, "r+b") as f:
            f.write(data)
    else:
        fb.seek(0)
        fb.write(data)


# ---------------------------------------------------------------------------
# Touch input — auto-discover the resistive touchscreen and self-calibrate
# from its reported ABS_X/ABS_Y range instead of hardcoding raw ADC bounds.
# ---------------------------------------------------------------------------

class Touch:
    def __init__(self):
        self.device = None
        self.x_min = self.x_max = self.y_min = self.y_max = None
        self._find_device()

    def _find_device(self):
        import evdev

        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            if "touch" in dev.name.lower() or "ads7846" in dev.name.lower():
                caps = dev.capabilities().get(evdev.ecodes.EV_ABS, [])
                caps = dict(caps)
                x_info = caps.get(evdev.ecodes.ABS_X)
                y_info = caps.get(evdev.ecodes.ABS_Y)
                if x_info and y_info:
                    self.device = dev
                    self.x_min, self.x_max = x_info.min, x_info.max
                    self.y_min, self.y_max = y_info.min, y_info.max
                    return
        print(f"[touch] no touchscreen evdev device found, running display-only", file=sys.stderr)

    def poll(self):
        """Return (x, y) in screen pixels on tap-release, else None. Non-blocking."""
        if self.device is None:
            return None
        import evdev

        sel = selectors.DefaultSelector()
        sel.register(self.device.fd, selectors.EVENT_READ)
        if not sel.select(timeout=0):
            sel.close()
            return None
        sel.close()

        raw_x = raw_y = None
        released = False
        try:
            for event in self.device.read():
                if event.type == evdev.ecodes.EV_ABS:
                    if event.code == evdev.ecodes.ABS_X:
                        raw_x = event.value
                    elif event.code == evdev.ecodes.ABS_Y:
                        raw_y = event.value
                elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH:
                    if event.value == 0:
                        released = True
        except BlockingIOError:
            return None

        if not released or raw_x is None or raw_y is None:
            return None
        sx = int((raw_x - self.x_min) / (self.x_max - self.x_min) * FB_W)
        sy = int((raw_y - self.y_min) / (self.y_max - self.y_min) * FB_H)
        return max(0, min(FB_W - 1, sx)), max(0, min(FB_H - 1, sy))


# ---------------------------------------------------------------------------
# Network — login once, stream metrics over the same /ws feed the Vue
# frontend uses, re-authenticating whenever the socket drops.
# ---------------------------------------------------------------------------

class MetricsFeed:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.latest = None
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self.latest

    def _set(self, snapshot):
        with self._lock:
            self.latest = snapshot

    def _login(self) -> str:
        body = json.dumps({"username": self.username, "password": self.password}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/v1/auth/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
        if "access_token" not in payload:
            raise RuntimeError("login did not return access_token — is TOTP enabled on this account?")
        return payload["access_token"]

    async def _run(self):
        import websockets

        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        while True:
            try:
                token = await asyncio.to_thread(self._login)
                async with websockets.connect(f"{ws_base}/ws?token={token}") as ws:
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "metrics":
                            self._set(msg)
            except (urllib.error.URLError, OSError, Exception) as exc:
                print(f"[feed] {exc!r}, retrying in 3s", file=sys.stderr)
                await asyncio.sleep(3)

    def start_background(self):
        threading.Thread(target=lambda: asyncio.run(self._run()), daemon=True).start()


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def bar(draw, x, y, w, h, pct, color=ACCENT):
    draw.rectangle([x, y, x + w, y + h], outline=BORDER, width=1)
    fill_w = int((w - 2) * max(0, min(100, pct)) / 100)
    if fill_w > 0:
        draw.rectangle([x + 1, y + 1, x + 1 + fill_w, y + h - 1], fill=color)


def pct_color(pct):
    if pct >= 90:
        return DANGER
    if pct >= 70:
        return WARNING
    return ACCENT


def draw_tabs(draw, active):
    y0 = FB_H - TAB_H
    draw.line([0, y0, FB_W, y0], fill=BORDER, width=1)
    tab_w = FB_W // len(PAGES)
    f = font(14, bold=True)
    for i, name in enumerate(PAGES):
        x0 = i * tab_w
        active_tab = i == active
        if active_tab:
            draw.rectangle([x0, y0 + 1, x0 + tab_w, FB_H], fill=(20, 24, 22))
        color = ACCENT if active_tab else FG_MUTED
        draw.text((x0 + tab_w // 2, y0 + TAB_H // 2), name.upper(), font=f, fill=color, anchor="mm")


def draw_overview(draw, snap):
    f_big = font(28, bold=True)
    f_lbl = font(13)
    f_sm = font(12)

    cpu = snap["cpu"]["aggregate"]
    mem = snap["memory"]["percent"]
    temps = snap["cpu"].get("temps") or []
    temp = temps[0]["temp_c"] if temps else None
    host = snap["system"]["hostname"]

    draw.text((10, 6), host, font=f_lbl, fill=FG_MUTED)

    draw.text((10, 24), "CPU", font=f_lbl, fill=FG_MUTED)
    draw.text((10, 40), f"{cpu:4.0f}%", font=f_big, fill=pct_color(cpu))
    bar(draw, 100, 55, 180, 10, cpu, pct_color(cpu))

    draw.text((300, 24), "MEM", font=f_lbl, fill=FG_MUTED)
    draw.text((300, 40), f"{mem:4.0f}%", font=f_big, fill=pct_color(mem))
    bar(draw, 300, 75, 170, 10, mem, pct_color(mem))

    if temp is not None:
        draw.text((10, 95), f"temp  {temp:.1f}C", font=f_sm, fill=FG_MUTED)

    cores = snap["cpu"].get("per_core") or []
    core_y = 120
    core_w = (FB_W - 20) / max(1, len(cores))
    for i, c in enumerate(cores):
        cx = 10 + int(i * core_w)
        h = int(c / 100 * 60)
        draw.rectangle([cx, core_y + 60 - h, cx + max(2, int(core_w) - 2), core_y + 60],
                       fill=pct_color(c))
    draw.line([10, core_y + 61, FB_W - 10, core_y + 61], fill=BORDER, width=1)

    uptime_s = snap["system"]["uptime_seconds"]
    hrs = int(uptime_s // 3600)
    draw.text((10, 195), f"uptime {hrs}h", font=f_sm, fill=FG_MUTED)


def draw_disks(draw, snap):
    f_lbl = font(13, bold=True)
    f_sm = font(12)
    draw.text((10, 6), "DISKS", font=f_lbl, fill=FG_MUTED)
    y = 26
    for d in snap.get("disks", [])[:4]:
        pct = d["usage_percent"]
        draw.text((10, y), d["mountpoint"][:14], font=f_sm, fill=FG)
        bar(draw, 120, y + 2, 200, 10, pct, pct_color(pct))
        draw.text((330, y), f"{pct:.0f}%", font=f_sm, fill=FG_MUTED)
        y += 22

    y += 10
    draw.text((10, y), "NETWORK", font=f_lbl, fill=FG_MUTED)
    y += 20
    for n in snap.get("network", [])[:3]:
        draw.text((10, y), n["interface"][:10], font=f_sm, fill=FG)
        draw.text((120, y), f"down {n['rx_mb_s']:.1f} MB/s", font=f_sm, fill=FG_MUTED)
        draw.text((300, y), f"up {n['tx_mb_s']:.1f} MB/s", font=f_sm, fill=FG_MUTED)
        y += 18


def draw_waiting(draw):
    f = font(16)
    draw.text((FB_W // 2, FB_H // 2), "connecting...", font=f, fill=FG_MUTED, anchor="mm")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(config_path):
    cfg = json.loads(Path(config_path).read_text())
    feed = MetricsFeed(cfg["base_url"], cfg["username"], cfg["password"])
    feed.start_background()
    touch = Touch()

    page = 0
    fb = open(FB_DEVICE, "r+b")
    frame_budget = 1 / 30

    try:
        while True:
            t0 = time.monotonic()

            tap = touch.poll()
            if tap is not None:
                tx, ty = tap
                if ty >= FB_H - TAB_H:
                    page = min(len(PAGES) - 1, tx // (FB_W // len(PAGES)))

            img = Image.new("RGB", (FB_W, FB_H), BG)
            draw = ImageDraw.Draw(img)
            snap = feed.get()
            if snap is None:
                draw_waiting(draw)
            elif PAGES[page] == "overview":
                draw_overview(draw, snap)
            else:
                draw_disks(draw, snap)
            draw_tabs(draw, page)

            write_frame(img, fb)

            elapsed = time.monotonic() - t0
            time.sleep(max(0, frame_budget - elapsed))
    except KeyboardInterrupt:
        pass
    finally:
        fb.close()


def _selftest():
    img = Image.new("RGB", (2, 1), (0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0))   # pure red   -> 0xF800
    img.putpixel((1, 0), (0, 0, 255))   # pure blue  -> 0x001F
    data = pack_fb_bytes(img)
    assert len(data) == 2 * 2, f"expected 4 bytes for 2 16bpp pixels, got {len(data)}"
    assert data[0:2] == b"\x00\xf8", f"red packed wrong: {data[0:2].hex()}"
    assert data[2:4] == b"\x1f\x00", f"blue packed wrong: {data[2:4].hex()}"
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} config.json", file=sys.stderr)
        sys.exit(1)
    else:
        main(sys.argv[1])
