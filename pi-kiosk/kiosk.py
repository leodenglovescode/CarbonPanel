#!/usr/bin/env python3
"""CarbonPanel kiosk client for a Pi driving a small SPI framebuffer (e.g.
/dev/fb1 from the fbtft/ili9486 driver). No X11, no browser — draws frames
with Pillow straight into the fb device node and reads the resistive
touchscreen straight off its evdev node. Targets the fb's native refresh
budget (~30fps) instead of a browser's DOM/animation overhead.

Setup on the Pi — one-shot installer (clones this repo, sets up the venv,
prompts for CarbonPanel base_url/username/password, installs the systemd
service; safe to re-run for updates):
    curl -fsSL https://raw.githubusercontent.com/leodenglovescode/CarbonPanel/master/pi-kiosk/install.sh | bash

Or by hand:
    cd pi-kiosk
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    cp config.example.json config.json   # fill in base_url/username/password
    .venv/bin/python kiosk.py config.json

Run `python3 kiosk.py --selftest` to sanity-check the framebuffer pixel
packing without touching real hardware, or `--touch-debug` to find the
right "touch_rotate" value for config.json if taps land in the wrong spot.
"""
import asyncio
import json
import selectors
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
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
CARD_BG = (17, 19, 18)
FG = (230, 240, 235)
FG_MUTED = (130, 145, 138)
ACCENT = (0, 255, 136)
WARNING = (255, 180, 40)
DANGER = (255, 70, 70)
BORDER = (40, 48, 44)
CARD_RADIUS = 6

TAB_H = 34
MARGIN = 4
GAP = 4
PAGES = ["overview", "disks", "procs"]
PAGE_DRAW = {}  # filled in after the draw_* functions are defined below


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

def _rotate_norm(fx, fy, rotate):
    """Map a touch-native normalized (fx,fy) in [0,1]^2 to screen-native
    normalized (gx,gy). The ili9486 dtoverlay's rotate= only rotates the
    *display* — the ADS7846 touch chip's raw axes are independent of it, so
    without this the touch position is very likely off by a 90/180/270
    rotation relative to what's on screen even though the tap itself works."""
    if rotate == 90:
        return fy, 1 - fx
    if rotate == 180:
        return 1 - fx, 1 - fy
    if rotate == 270:
        return 1 - fy, fx
    return fx, fy


class Touch:
    def __init__(self, rotate=90):
        self.device = None
        self.x_min = self.x_max = self.y_min = self.y_max = None
        self.last_x = self.last_y = None
        self.rotate = rotate
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

        released = False
        try:
            for event in self.device.read():
                if event.type == evdev.ecodes.EV_ABS:
                    # cache position as it streams in — a release event often
                    # arrives in its own batch with no fresh X/Y alongside it
                    if event.code == evdev.ecodes.ABS_X:
                        self.last_x = event.value
                    elif event.code == evdev.ecodes.ABS_Y:
                        self.last_y = event.value
                elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH:
                    if event.value == 0:
                        released = True
        except BlockingIOError:
            return None

        if not released or self.last_x is None or self.last_y is None:
            return None
        fx = (self.last_x - self.x_min) / (self.x_max - self.x_min)
        fy = (self.last_y - self.y_min) / (self.y_max - self.y_min)
        gx, gy = _rotate_norm(fx, fy, self.rotate)
        sx, sy = int(gx * FB_W), int(gy * FB_H)
        return max(0, min(FB_W - 1, sx)), max(0, min(FB_H - 1, sy))


# ---------------------------------------------------------------------------
# Network — login once, stream metrics over the same /ws feed the Vue
# frontend uses, re-authenticating whenever the socket drops.
# ---------------------------------------------------------------------------

HISTORY_LEN = 60  # sparkline window, in samples (60 * 0.5s interval = 30s)


class MetricsFeed:
    def __init__(self, base_url, username, password, interval=0.5):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.interval = interval
        self.latest = None
        self.cpu_hist = deque(maxlen=HISTORY_LEN)
        self.mem_hist = deque(maxlen=HISTORY_LEN)
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self.latest

    def get_history(self):
        with self._lock:
            return list(self.cpu_hist), list(self.mem_hist)

    def _set(self, snapshot):
        with self._lock:
            self.latest = snapshot
            self.cpu_hist.append(snapshot["cpu"]["aggregate"])
            self.mem_hist.append(snapshot["memory"]["percent"])

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
                    await ws.send(json.dumps({"type": "set_interval", "seconds": self.interval}))
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
    r = h / 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, outline=BORDER, width=1)
    fill_w = int((w - 2) * max(0, min(100, pct)) / 100)
    if fill_w > 2:
        draw.rounded_rectangle([x + 1, y + 1, x + 1 + fill_w, y + h - 1], radius=max(1, r - 1), fill=color)


def pct_color(pct):
    if pct >= 90:
        return DANGER
    if pct >= 70:
        return WARNING
    return ACCENT


def sparkline(draw, x, y, w, h, values, color=ACCENT, max_val=100):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=4, outline=BORDER, width=1)
    if len(values) < 2:
        return
    step = w / (len(values) - 1)
    pts = [
        (x + i * step, y + h - (max(0, min(max_val, v)) / max_val) * h)
        for i, v in enumerate(values)
    ]
    draw.line(pts, fill=color, width=2)


def card(draw, x, y, w, h, title):
    """Rounded container matching the real dashboard's widget cards
    (--bg-card/--border/--radius in main.css). Returns the inner content
    origin (x, y) below the title, for callers to draw into."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=CARD_RADIUS, fill=CARD_BG, outline=BORDER, width=1)
    f = font(11, bold=True)
    draw.text((x + 8, y + 6), title.upper(), font=f, fill=FG_MUTED)
    return x + 8, y + 22


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


# Overview/disks page grid: 2 cols x 2 rows + 1 full-width row, mirroring
# the real dashboard's separate CpuWidget/RamWidget/SystemWidget/etc cards
# (frontend/src/components/widgets/) rather than one wall of numbers.
COL_W = (FB_W - 2 * MARGIN - GAP) / 2
ROW_H = 90
COL1_X = MARGIN
COL2_X = MARGIN + COL_W + GAP
ROW1_Y = MARGIN
ROW2_Y = ROW1_Y + ROW_H + GAP
ROW3_Y = ROW2_Y + ROW_H + GAP
FULL_W = FB_W - 2 * MARGIN


def draw_overview(draw, snap, hist):
    f_big = font(24, bold=True)
    f_sm = font(12)
    cpu_hist, mem_hist = hist

    cpu = snap["cpu"]["aggregate"]
    cx, cy = card(draw, COL1_X, ROW1_Y, COL_W, ROW_H, "CPU")
    draw.text((cx, cy), f"{cpu:3.0f}%", font=f_big, fill=pct_color(cpu))
    sparkline(draw, cx, cy + 32, COL_W - 16, 28, cpu_hist, pct_color(cpu))

    mem = snap["memory"]["percent"]
    cx, cy = card(draw, COL2_X, ROW1_Y, COL_W, ROW_H, "MEM")
    draw.text((cx, cy), f"{mem:3.0f}%", font=f_big, fill=pct_color(mem))
    sparkline(draw, cx, cy + 32, COL_W - 16, 28, mem_hist, pct_color(mem))

    cx, cy = card(draw, COL1_X, ROW2_Y, COL_W, ROW_H, "System")
    temps = snap["cpu"].get("temps") or []
    temp = temps[0]["temp_c"] if temps else None
    load1 = (snap["cpu"].get("load_avg") or [None])[0]
    uptime_s = snap["system"]["uptime_seconds"]
    draw.text((cx, cy), snap["system"]["hostname"][:18], font=f_sm, fill=FG)
    if temp is not None:
        draw.text((cx, cy + 16), f"temp   {temp:.1f}C", font=f_sm, fill=FG_MUTED)
    if load1 is not None:
        draw.text((cx, cy + 32), f"load   {load1:.2f}", font=f_sm, fill=FG_MUTED)
    draw.text((cx, cy + 48), f"uptime {int(uptime_s // 3600)}h", font=f_sm, fill=FG_MUTED)

    cx, cy = card(draw, COL2_X, ROW2_Y, COL_W, ROW_H, "Network")
    nets = snap.get("network", [])[:2]
    if not nets:
        draw.text((cx, cy), "no interfaces", font=f_sm, fill=FG_MUTED)
    for i, n in enumerate(nets):
        yy = cy + i * 32
        draw.text((cx, yy), n["interface"][:12], font=f_sm, fill=FG)
        draw.text((cx, yy + 16), f"d {n['rx_mb_s']:.1f}  u {n['tx_mb_s']:.1f} MB/s", font=f_sm, fill=FG_MUTED)

    cx, cy = card(draw, COL1_X, ROW3_Y, FULL_W, ROW_H, "Cores")
    cores = snap["cpu"].get("per_core") or []
    core_h = 46
    core_w = (FULL_W - 16) / max(1, len(cores))
    for i, c in enumerate(cores):
        bx = cx + int(i * core_w)
        h = int(c / 100 * core_h)
        draw.rectangle([bx, cy + core_h - h, bx + max(2, int(core_w) - 2), cy + core_h],
                       fill=pct_color(c))
    if snap["gpu"]["available"] and snap["gpu"]["devices"]:
        gpu = snap["gpu"]["devices"][0]
        draw.text((cx, cy + core_h + 4), f"gpu {gpu['utilization_percent']:.0f}%", font=f_sm, fill=FG_MUTED)


def draw_disks(draw, snap, hist):
    f_sm = font(12)
    disk_h = 134
    cx, cy = card(draw, COL1_X, MARGIN, FULL_W, disk_h, "Disks")
    y = cy
    for d in snap.get("disks", [])[:4]:
        pct = d["usage_percent"]
        draw.text((cx, y), d["mountpoint"][:12], font=f_sm, fill=FG)
        bar(draw, cx + 100, y + 2, 140, 10, pct, pct_color(pct))
        draw.text((cx + 250, y), f"{pct:.0f}%", font=f_sm, fill=FG_MUTED)
        draw.text((cx + 300, y), f"r{d['read_mb_s']:.0f}/w{d['write_mb_s']:.0f} MB/s", font=f_sm, fill=FG_MUTED)
        y += 22

    net_y = MARGIN + disk_h + GAP
    cx, cy = card(draw, COL1_X, net_y, FULL_W, FB_H - TAB_H - net_y - MARGIN, "Network")
    y = cy
    for n in snap.get("network", [])[:4]:
        draw.text((cx, y), n["interface"][:10], font=f_sm, fill=FG)
        draw.text((cx + 110, y), f"down {n['rx_mb_s']:.1f} MB/s", font=f_sm, fill=FG_MUTED)
        draw.text((cx + 290, y), f"up {n['tx_mb_s']:.1f} MB/s", font=f_sm, fill=FG_MUTED)
        y += 18


def draw_procs(draw, snap, hist):
    f_sm = font(12)
    cx, cy = card(draw, COL1_X, MARGIN, FULL_W, FB_H - TAB_H - 2 * MARGIN, "Processes")
    y = cy
    procs = sorted(snap.get("processes", []), key=lambda p: p["cpu_percent"], reverse=True)
    for p in procs[:14]:
        draw.text((cx, y), p["name"][:18], font=f_sm, fill=FG)
        draw.text((cx + 250, y), f"{p['cpu_percent']:.0f}%", font=f_sm,
                   fill=pct_color(p["cpu_percent"]), anchor="ra")
        draw.text((cx + 330, y), f"{p['memory_mb']:.0f}MB", font=f_sm, fill=FG_MUTED, anchor="ra")
        y += 18


def draw_waiting(draw):
    f = font(16)
    draw.text((FB_W // 2, FB_H // 2), "connecting...", font=f, fill=FG_MUTED, anchor="mm")


PAGE_DRAW.update({"overview": draw_overview, "disks": draw_disks, "procs": draw_procs})


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(config_path):
    cfg = json.loads(Path(config_path).read_text())
    feed = MetricsFeed(cfg["base_url"], cfg["username"], cfg["password"],
                        interval=cfg.get("interval", 0.5))
    feed.start_background()
    touch = Touch(rotate=cfg.get("touch_rotate", 90))

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
            else:
                PAGE_DRAW[PAGES[page]](draw, snap, feed.get_history())
            draw_tabs(draw, page)

            write_frame(img, fb)

            elapsed = time.monotonic() - t0
            time.sleep(max(0, frame_budget - elapsed))
    except KeyboardInterrupt:
        pass
    finally:
        fb.close()


def _touch_debug():
    """Prints raw touch position + the screen coords each touch_rotate value
    would produce. Tap each corner of the actual displayed screen and note
    which `rotate=` column matches reality — put that number in config.json
    as "touch_rotate". No config.json / network needed for this."""
    touch = Touch(rotate=0)
    if touch.device is None:
        print("no touchscreen device found", file=sys.stderr)
        return
    print("tap the screen (Ctrl-C to quit)...")
    while True:
        import evdev
        for event in touch.device.read_loop():
            if event.type == evdev.ecodes.EV_ABS:
                if event.code == evdev.ecodes.ABS_X:
                    touch.last_x = event.value
                elif event.code == evdev.ecodes.ABS_Y:
                    touch.last_y = event.value
            elif event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.BTN_TOUCH and event.value == 0:
                if touch.last_x is None or touch.last_y is None:
                    continue
                fx = (touch.last_x - touch.x_min) / (touch.x_max - touch.x_min)
                fy = (touch.last_y - touch.y_min) / (touch.y_max - touch.y_min)
                results = {r: _rotate_norm(fx, fy, r) for r in (0, 90, 180, 270)}
                print(f"raw=({touch.last_x},{touch.last_y}) " +
                      "  ".join(f"rot{r}=({int(g[0]*FB_W)},{int(g[1]*FB_H)})" for r, g in results.items()))


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
    elif "--touch-debug" in sys.argv:
        _touch_debug()
    elif len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} config.json", file=sys.stderr)
        sys.exit(1)
    else:
        main(sys.argv[1])
