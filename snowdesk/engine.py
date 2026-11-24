"""Grain snow: falling-sand stacks plus z-order occlusion.

Falling-sand games (Wikipedia: Falling-sand game) keep one particle per cell.
A grain falls if the cell below is empty, otherwise it slides to a lower neighbor.
Desktop toys use the same idea on a height field: each column is a stack of grains,
and a grain topples sideways when the slope is too steep (angle of repose).
Window occlusion is a 1D visibility test: at each x, the upper window's rectangle
hides the lower window's top edge. Maximized windows occlude but do not catch snow.
"""
from __future__ import annotations

import math
import time
import random
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

GRAIN = 4
MAX_STACK = 16
REPOSE = 1
PLOW_INTERVALS = (120, 180, 240, 360)


@dataclass
class Surface:
    key: str
    y: int
    x0: int
    x1: int
    height: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int16))
    jitter: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int8))

    def ensure(self) -> None:
        cols = max(1, (self.x1 - self.x0) // GRAIN)
        if self.height.size != cols:
            old = self.height
            self.height = np.zeros(cols, np.int16)
            self.jitter = np.zeros(cols, np.int8)
            if old.size:
                n = min(old.size, cols)
                self.height[:n] = old[:n]


@dataclass
class Flake:
    x: float
    y: float
    vy: float
    r: float
    vx: float = 0.0


def exposed_tops(windows: list[dict], screen_w: int, screen_h: int) -> list[tuple[str, int, int, int]]:
    """Return catch segments (key, y, x0, x1).

    windows are topmost-first. A lower top edge is hidden where a higher
    window rectangle covers that point. Maximized windows hide what is below
    but do not collect snow on their own top. The taskbar is not a window here.
    Uncovered columns land on the screen bottom.
    """
    catchers = []
    occluders = []
    for win in windows:
        left, top, right, bottom = win["left"], win["top"], win["right"], win["bottom"]
        if right - left < 40 or bottom - top < 40:
            continue
        if win.get("zoomed") or top <= 2:
            occluders.append((left, top, right, bottom))
            continue
        segments = _subtract(left, right, top, occluders)
        for x0, x1 in segments:
            if x1 - x0 >= GRAIN * 2:
                catchers.append((win["key"], top, x0, x1))
        occluders.append((left, top, right, bottom))
    ground = _subtract(0, screen_w, screen_h - 1, occluders)
    for x0, x1 in ground:
        if x1 - x0 >= GRAIN:
            catchers.append(("ground", screen_h - 1, x0, x1))
    return catchers


def _subtract(x0: int, x1: int, y: int, occluders: list[tuple[int, int, int, int]]) -> list[tuple[int, int]]:
    spans = [(x0, x1)]
    for left, top, right, bottom in occluders:
        if y < top or y >= bottom:
            continue
        nxt = []
        for a, b in spans:
            if b <= left or a >= right:
                nxt.append((a, b))
                continue
            if a < left:
                nxt.append((a, left))
            if right < b:
                nxt.append((right, b))
        spans = [(a, b) for a, b in nxt if b - a >= GRAIN]
    return spans


class World:
    def __init__(self, width: int, height: int, seed: int = 7) -> None:
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.surfaces: dict[str, Surface] = {}
        self.flakes: list[Flake] = []
        self.landing: list[tuple] = []
        self.car_x = -80.0
        self.car_active = False
        self.since_plow = 0.0
        self.plow_wait = float(self.rng.choice(PLOW_INTERVALS))

    def sync(self, windows: list[dict]) -> None:
        segs = exposed_tops(windows, self.width, self.height)
        self.landing = segs
        live = {"ground"}
        for win in windows:
            if win.get("zoomed") or win["top"] <= 2:
                continue
            if win["right"] - win["left"] < 40:
                continue
            live.add(win["key"])
            surf = self.surfaces.get(win["key"])
            if surf is None:
                surf = Surface(win["key"], win["top"], win["left"], win["right"])
                self.surfaces[win["key"]] = surf
            else:
                now = time.time()
                prev_t = getattr(surf, "seen", now)
                dt = max(0.016, min(0.12, now - prev_t))
                self._fling(surf, win["left"] - surf.x0, win["top"] - surf.y, dt)
                surf.seen = now
            surf.y, surf.x0, surf.x1 = win["top"], win["left"], win["right"]
            surf.ensure()
        ground_segs = [seg for seg in segs if seg[0] == "ground"]
        if ground_segs:
            _, y, x0, x1 = ground_segs[0]
            # Ground may be several exposed spans. Store one full-width pile.
            x0, x1 = 0, self.width
            surf = self.surfaces.get("ground")
            if surf is None:
                surf = Surface("ground", y, x0, x1)
                self.surfaces["ground"] = surf
            surf.y, surf.x0, surf.x1 = self.height - 1, x0, x1
            surf.ensure()
        for key in list(self.surfaces):
            if key not in live:
                del self.surfaces[key]

    def step(self, dt: float = 0.05) -> None:
        if self.rng.random() < 0.22:
            self.flakes.append(Flake(
                self.rng.uniform(0, self.width),
                self.rng.uniform(-8, 0),
                self.rng.uniform(28, 52),
                self.rng.choice((1.6, 2.0, 2.4, 2.8)),
            ))
        kept = []
        for flake in self.flakes:
            flake.x += flake.vx * dt
            flake.vx *= 0.90
            flake.y += flake.vy * dt
            hit = self._hit(flake.x, flake.y)
            if hit is None:
                if flake.y < self.height + 8:
                    kept.append(flake)
                continue
            surf, col = hit
            if surf.height[col] < MAX_STACK:
                surf.height[col] += 1
                if surf.jitter[col] == 0:
                    surf.jitter[col] = self.rng.choice((-1, 0, 1))
                self._avalanche(surf)
        self.flakes = kept[-180:]
        for surf in list(self.surfaces.values()):
            self._ceiling(surf)
            self._avalanche(surf)
        self.since_plow += dt
        if not self.car_active and self.since_plow >= self.plow_wait:
            self.car_active = True
            self.car_x = -90
            self.blade_x = self.car_x + 50
            self.since_plow = 0
            self.plow_wait = float(self.rng.choice(PLOW_INTERVALS))
            print(f"next plow in {int(self.plow_wait)}s", flush=True)
        if self.car_active:
            self.car_x += 70 * dt
            self._plow()
            if self.car_x > self.width + 90:
                self.car_active = False

    def _exposed(self, key: str, x: float) -> bool:
        for k, _y, x0, x1 in self.landing:
            if k == key and x0 <= x < x1:
                return True
        return False

    def _hit(self, x: float, y: float):
        best = None
        for surf in self.surfaces.values():
            if not self._exposed(surf.key, x):
                continue
            if x < surf.x0 or x >= surf.x1 or surf.height.size == 0:
                continue
            col = int((x - surf.x0) // GRAIN)
            if col < 0 or col >= surf.height.size:
                continue
            top = surf.y - int(surf.height[col]) * 2
            if y >= top - 1 and (best is None or top < best[0]):
                best = (top, surf, col)
        if best is None:
            return None
        return best[1], best[2]


    def _fling(self, surf: Surface, dx: float, dy: float, dt: float) -> None:
        dist = math.hypot(dx, dy)
        if dist < 8 or surf.height.size == 0:
            return
        speed = dist / dt
        severity = min(1.0, max(dist / 260.0, speed / 1700.0))
        if severity < 0.05:
            return
        vx = -dx / dt * 0.45
        vy = 24 + max(0.0, -dy / dt) * 0.12
        h = surf.height
        for i in range(int(h.size)):
            have = int(h[i])
            if have <= 0:
                continue
            lose = int(round(have * severity))
            if lose <= 0 and self.rng.random() < severity:
                lose = 1
            lose = min(have, lose)
            if lose <= 0:
                continue
            h[i] = have - lose
            x = surf.x0 + i * GRAIN + GRAIN // 2
            for n in range(lose):
                self.flakes.append(Flake(
                    x + self.rng.uniform(-4, 4),
                    surf.y - 4 - n * 2,
                    vy + self.rng.uniform(0, 36),
                    self.rng.choice((1.8, 2.2, 2.6)),
                    vx + self.rng.uniform(-50, 50),
                ))

    def _drop_off(self, surf: Surface, x: float) -> None:
        self.flakes.append(Flake(x, surf.y - 6, self.rng.uniform(36, 60), self.rng.choice((1.8, 2.2, 2.6))))

    def _avalanche(self, surf: Surface) -> None:
        h = surf.height
        n = int(h.size)
        if n == 0:
            return
        for _ in range(6):
            moved = False
            for i in range(n):
                left = int(h[i - 1]) if i else 0
                right = int(h[i + 1]) if i + 1 < n else 0
                here = int(h[i])
                if here >= left + REPOSE + 1 and here >= right:
                    h[i] = here - 1
                    if i == 0:
                        self._drop_off(surf, surf.x0 - 2)
                    else:
                        h[i - 1] = left + 1
                    moved = True
                elif here >= right + REPOSE + 1:
                    h[i] = here - 1
                    if i + 1 == n:
                        self._drop_off(surf, surf.x1 + 2)
                    else:
                        h[i + 1] = right + 1
                    moved = True
            if not moved:
                break

    def _ceiling(self, surf: Surface) -> None:
        # A grain at layer k sits near y = surf.y - 4 - k*3. It cannot cross y=0.
        max_k = max(0, (surf.y - 6) // 3)
        h = surf.height
        n = int(h.size)
        for i in range(n):
            extra = int(h[i]) - max_k
            if extra <= 0:
                continue
            h[i] = max_k
            self._push_out(surf, i, -1, extra // 2, max_k)
            self._push_out(surf, i, 1, extra - extra // 2, max_k)

    def _push_out(self, surf: Surface, origin: int, direction: int, count: int, max_k: int) -> None:
        h = surf.height
        n = int(h.size)
        for _ in range(count):
            placed = False
            j = origin
            while 0 <= j + direction < n:
                j += direction
                if int(h[j]) < max_k:
                    h[j] = int(h[j]) + 1
                    placed = True
                    break
            if not placed:
                self._drop_off(surf, surf.x0 - 3 if direction < 0 else surf.x1 + 3)

    def _plow(self) -> None:
        ground = self.surfaces.get("ground")
        if ground is None or ground.height.size == 0:
            return
        blade = self.car_x + 50
        prev = getattr(self, "blade_x", blade)
        self.blade_x = blade
        if blade < 0 and prev < 0:
            return
        a, b = (prev, blade) if prev <= blade else (blade, prev)
        c0 = max(0, int((a - ground.x0) // GRAIN))
        c1 = min(ground.height.size, int((b - ground.x0) // GRAIN) + 1)
        if 0 <= c0 < c1:
            ground.height[c0:c1] = 0

    def disturb(self, mx: float, my: float, dx: float) -> None:
        # Hovering a pile knocks a little snow loose; moving the mouse pushes more.
        radius = 22
        for surf in self.surfaces.values():
            if surf.height.size == 0 or int(surf.height.max()) <= 0:
                continue
            top = surf.y - int(surf.height.max()) * 3
            if my < top - 10 or my > surf.y + 12:
                continue
            for i, count in enumerate(surf.height):
                if count <= 0:
                    continue
                x = surf.x0 + i * GRAIN + GRAIN // 2
                if abs(x - mx) > radius:
                    continue
                shove = min(1.0, 0.18 + abs(dx) * 0.12)
                lose = min(int(count), 1 if shove < 0.45 else 2)
                if self.rng.random() > shove:
                    continue
                surf.height[i] = int(count) - lose
                side = 1 if dx >= 0 else -1
                for _ in range(lose):
                    self.flakes.append(Flake(
                        x + self.rng.uniform(-3, 3),
                        surf.y - 8,
                        self.rng.uniform(-70, -28),
                        self.rng.choice((1.6, 2.0, 2.4)),
                        side * self.rng.uniform(20, 90) + dx * 2,
                    ))

    def render(self) -> Image.Image:
        im = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        for surf in self.surfaces.values():
            self._draw_mound(draw, surf)
        for flake in self.flakes:
            r = flake.r
            draw.ellipse((flake.x - r, flake.y - r, flake.x + r, flake.y + r), fill=(255, 255, 255, 235))
        if self.car_active:
            _draw_plow(draw, int(self.car_x), self.height - 16)
        return im

    def _draw_mound(self, draw: ImageDraw.ImageDraw, surf: Surface) -> None:
        h = surf.height.astype(float)
        if h.size == 0 or float(h.max()) < 0.4:
            return
        kernel = np.array([1, 2, 3, 2, 1], dtype=float)
        kernel /= kernel.sum()
        smooth = np.convolve(h, kernel, mode="same")
        run = []
        def flush():
            if len(run) < 2:
                run.clear()
                return
            top = [(x, y) for x, y in run]
            base_y = surf.y + 3
            poly = top + [(top[-1][0], base_y), (top[0][0], base_y)]
            shade = [(x, y + 3) for x, y in top] + [(top[-1][0], base_y + 3), (top[0][0], base_y + 3)]
            draw.polygon(shade, fill=(226, 236, 247, 180))
            draw.polygon(poly, fill=(255, 255, 255, 230))
            draw.line(top, fill=(205, 220, 238, 220), width=1)
            run.clear()
        for i, val in enumerate(smooth):
            x = surf.x0 + i * GRAIN + GRAIN // 2
            if val < 0.35 or not self._exposed(surf.key, x):
                flush()
                continue
            run.append((x, surf.y - val * 2.6))
        flush()

def _disc() -> np.ndarray:
    s = 7
    yy, xx = np.mgrid[-3:4, -3:4]
    dist = np.sqrt(xx * xx + yy * yy)
    alpha = np.clip(1.15 - dist / 2.4, 0, 1)
    disc = np.zeros((s, s, 4), np.float32)
    disc[..., 0] = 246
    disc[..., 1] = 250
    disc[..., 2] = 255
    disc[..., 3] = alpha * 230
    return disc


def _stamp(img: np.ndarray, kernel: np.ndarray, x: int, y: int, scale: float = 1.0) -> None:
    kh, kw = kernel.shape[:2]
    x0, y0 = int(x), int(y)
    if x0 >= img.shape[1] or y0 >= img.shape[0] or x0 + kw <= 0 or y0 + kh <= 0:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dw = min(kw - sx0, img.shape[1] - dx0)
    dh = min(kh - sy0, img.shape[0] - dy0)
    if dw <= 0 or dh <= 0:
        return
    src = kernel[sy0:sy0 + dh, sx0:sx0 + dw]
    dst = img[dy0:dy0 + dh, dx0:dx0 + dw].astype(np.float32)
    a = (src[..., 3:4] / 255.0) * scale
    out = src[..., :3] * a + dst[..., :3] * (1 - a)
    dst[..., :3] = out
    dst[..., 3] = np.maximum(dst[..., 3], src[..., 3] * scale)
    img[dy0:dy0 + dh, dx0:dx0 + dw] = dst.astype(np.uint8)


def _draw_plow(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    # Half the reference plow: orange body, pale window, gray blade, dark wheels.
    draw.rounded_rectangle((x + 21, y - 14, x + 55, y), radius=2, fill=(243, 156, 18, 255))
    draw.rectangle((x + 28, y - 20, x + 42, y - 12), fill=(174, 227, 255, 255))
    draw.polygon([(x + 55, y - 10), (x + 70, y - 4), (x + 55, y - 2)], fill=(90, 96, 100, 255))
    draw.ellipse((x + 26, y - 5, x + 34, y + 3), fill=(44, 44, 44, 255))
    draw.ellipse((x + 44, y - 5, x + 52, y + 3), fill=(44, 44, 44, 255))
    draw.rectangle((x + 48, y - 16, x + 52, y - 12), fill=(231, 76, 60, 255))


def self_check() -> None:
    windows = [
        {"key": "A", "left": 0, "top": 100, "right": 400, "bottom": 400, "zoomed": False},
        {"key": "B", "left": 200, "top": 250, "right": 700, "bottom": 520, "zoomed": False},
        {"key": "M", "left": 800, "top": 0, "right": 1000, "bottom": 700, "zoomed": True},
    ]
    segs = exposed_tops(windows, 1000, 700)
    by_key = {}
    for key, y, x0, x1 in segs:
        by_key.setdefault(key, []).append((y, x0, x1))
    assert any(x0 == 0 and x1 == 400 for _, x0, x1 in by_key["A"]), by_key
    assert any(x0 == 400 and x1 == 700 for _, x0, x1 in by_key["B"]), by_key
    assert "M" not in by_key
    assert any(x0 == 0 and x1 == 800 for _, x0, x1 in by_key["ground"]), by_key
    print("occlusion ok", by_key)
