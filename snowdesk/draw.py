"""Original cabin and snowman art. Not taken from the video."""
from __future__ import annotations

import random
from PIL import Image, ImageDraw, ImageFilter

HATS = (
    "santa", "tophat", "bobble", "crown", "cowboy",
    "elf", "viking", "antlers", "pirate", "headphones", "none",
)


def _glow(base: Image.Image, color, xy, radius: int, alpha: int = 90) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = xy
    d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, alpha))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(1, radius // 3))))


def _pine(d: ImageDraw.ImageDraw, x: int, y: int, h: int, color) -> None:
    d.polygon([(x, y - h), (x - h // 3, y), (x + h // 3, y)], fill=color)
    d.rectangle((x - 5, y - 6, x + 5, y + 16), fill=(78, 52, 34, 255))


def _cabin(im: Image.Image, x: int, ground: int, scale: float = 1.0) -> None:
    d = ImageDraw.Draw(im)
    s = lambda v: int(v * scale)
    wall_l, wall_r = x, x + s(340)
    wall_t, wall_b = ground - s(210), ground
    d.polygon(
        [(wall_l - s(16), wall_t + s(10)), (x + s(170), wall_t - s(150)), (wall_r + s(16), wall_t + s(10))],
        fill=(236, 242, 248, 255),
    )
    d.rectangle((wall_l, wall_t, wall_r, wall_b), fill=(122, 72, 42, 255))
    for i in range(8):
        yy = wall_t + s(12) + i * s(24)
        d.line((wall_l, yy, wall_r, yy), fill=(92, 52, 30, 255), width=max(2, s(3)))
    d.rounded_rectangle((x + s(146), wall_b - s(110), x + s(196), wall_b), radius=s(6), fill=(64, 36, 24, 255))
    d.ellipse((x + s(180), wall_b - s(58), x + s(188), wall_b - s(50)), fill=(232, 190, 90, 255))
    for wx in (x + s(36), x + s(230)):
        _glow(im, (255, 176, 64), (wx + s(28), wall_t + s(78)), s(46), 70)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((wx, wall_t + s(36), wx + s(56), wall_t + s(96)), radius=s(4), fill=(255, 196, 92, 255))
        d.line((wx + s(28), wall_t + s(36), wx + s(28), wall_t + s(96)), fill=(122, 72, 42, 255), width=max(2, s(3)))
        d.line((wx, wall_t + s(66), wx + s(56), wall_t + s(66)), fill=(122, 72, 42, 255), width=max(2, s(3)))
    d = ImageDraw.Draw(im)
    for i, lx in enumerate(range(wall_l - s(8), wall_r + s(8), s(22))):
        ly = wall_t + s(6) + (i % 2) * s(8)
        col = ((255, 84, 72), (255, 210, 86), (86, 196, 255))[i % 3]
        _glow(im, col, (lx, ly), s(10), 80)
        d = ImageDraw.Draw(im)
        d.ellipse((lx - s(3), ly - s(3), lx + s(3), ly + s(3)), fill=(*col, 255))
    d.rectangle((x - s(28), wall_t + s(40), x - s(22), wall_t + s(78)), fill=(70, 48, 32, 255))
    _glow(im, (255, 170, 60), (x - s(25), wall_t + s(96)), s(28), 100)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x - s(40), wall_t + s(78), x - s(10), wall_t + s(114)), radius=s(4), fill=(255, 186, 72, 255))


def make_cabin(width: int = 2800, height: int = 1080) -> Image.Image:
    im = Image.new("RGBA", (width, height), (8, 18, 42, 255))
    d = ImageDraw.Draw(im)
    horizon = int(height * 0.62)
    for y in range(0, horizon, 6):
        t = y / horizon
        col = (int(10 + 22 * t), int(20 + 40 * t), int(52 + 55 * (1 - abs(t - 0.4))), 255)
        d.rectangle((0, y, width, y + 6), fill=col)
    rng = random.Random(24)
    for _ in range(160):
        x, y = rng.randint(0, width - 1), rng.randint(8, horizon - 24)
        s = 2 if rng.random() < 0.2 else 1
        d.ellipse((x, y, x + s, y + s), fill=(255, 248, 230, 210))
    d.ellipse((width - 420, 70, width - 280, 210), fill=(255, 244, 214, 255))
    d.ellipse((width - 390, 58, width - 250, 198), fill=(10, 24, 58, 255))
    peaks = [
        (0, horizon), (180, horizon - 150), (420, horizon - 40), (700, horizon - 210),
        (980, horizon - 70), (1280, horizon - 240), (1600, horizon - 90),
        (1900, horizon - 180), (2200, horizon - 50), (2500, horizon - 160),
        (width, horizon - 80), (width, horizon),
    ]
    d.polygon(peaks, fill=(62, 92, 138, 255))
    snow_peaks = [(x, horizon if i in (0, len(peaks) - 1) else y + 28) for i, (x, y) in enumerate(peaks)]
    d.polygon(snow_peaks, fill=(214, 228, 242, 255))
    for x in range(40, width, 74):
        _pine(d, x, horizon + 8, 64 + (x * 17) % 46, (28, 58, 78, 255))
    ground = horizon + 36
    _cabin(im, 360, ground)
    _cabin(im, 1680, ground + 8, 0.72)
    d = ImageDraw.Draw(im)
    for x in (120, 760, 980, 1400, 2100, 2460):
        _pine(d, x, ground + 18, 150 + (x % 5) * 16, (18, 72, 58, 255))
    for x in range(640, 980, 36):
        d.rectangle((x, ground - 46, x + 6, ground), fill=(92, 64, 42, 255))
    d.polygon([(630, ground - 36), (1000, ground - 52), (1000, ground - 44), (630, ground - 28)], fill=(122, 86, 54, 255))
    d.ellipse((0, ground - 8, width, height + 30), fill=(236, 244, 250, 255))
    return im


def make_snowman(hat: str = "santa", blink: bool = False) -> Image.Image:
    w, h = 240, 320
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((18, 278, 222, 316), fill=(226, 236, 246, 220))
    d.ellipse((36, 286, 204, 312), fill=(255, 255, 255, 240))
    cx, body_y, mid_y, head_y = 120, 214, 156, 108
    d.ellipse((cx - 58, body_y - 52, cx + 58, body_y + 52), fill=(255, 255, 255, 255))
    d.ellipse((cx - 42, mid_y - 40, cx + 42, mid_y + 40), fill=(255, 255, 255, 255))
    d.ellipse((cx - 30, head_y - 30, cx + 30, head_y + 30), fill=(255, 255, 255, 255))
    d.line((cx - 40, mid_y, cx - 78, mid_y - 28), fill=(92, 62, 36, 255), width=4)
    d.line((cx + 40, mid_y, cx + 78, mid_y - 24), fill=(92, 62, 36, 255), width=4)
    for by in (mid_y - 8, mid_y + 14, body_y - 8):
        d.ellipse((cx - 4, by, cx + 4, by + 8), fill=(42, 42, 48, 255))
    eye_h = 3 if blink else 7
    eye_y = head_y - 4
    d.ellipse((cx - 14, eye_y, cx - 7, eye_y + eye_h), fill=(32, 32, 36, 255))
    d.ellipse((cx + 7, eye_y, cx + 14, eye_y + eye_h), fill=(32, 32, 36, 255))
    d.polygon([(cx - 2, head_y + 2), (cx + 10, head_y + 6), (cx - 1, head_y + 8)], fill=(232, 122, 42, 255))
    d.arc((cx - 12, head_y + 6, cx + 12, head_y + 20), 20, 160, fill=(32, 32, 36, 255), width=2)
    d.polygon([(cx - 18, head_y + 26), (cx + 22, head_y + 24), (cx + 16, head_y + 38), (cx - 22, head_y + 40)], fill=(196, 40, 48, 255))
    d.polygon([(cx + 8, head_y + 32), (cx + 18, head_y + 34), (cx + 14, head_y + 62), (cx + 4, head_y + 60)], fill=(196, 40, 48, 255))
    _hat(d, im, hat, cx, head_y)
    return im


def _hat(d, im, hat, cx, head_y) -> None:
    if hat == "none":
        return
    if hat == "santa":
        d.polygon([(cx - 28, head_y - 18), (cx + 26, head_y - 16), (cx + 8, head_y - 78)], fill=(196, 36, 42, 255))
        d.ellipse((cx - 34, head_y - 28, cx + 32, head_y - 10), fill=(255, 255, 255, 255))
        d.ellipse((cx - 2, head_y - 92, cx + 22, head_y - 68), fill=(255, 255, 255, 255))
    elif hat == "tophat":
        d.rectangle((cx - 22, head_y - 62, cx + 22, head_y - 16), fill=(28, 28, 32, 255))
        d.rectangle((cx - 36, head_y - 22, cx + 36, head_y - 10), fill=(28, 28, 32, 255))
        d.rectangle((cx - 22, head_y - 28, cx + 22, head_y - 22), fill=(196, 40, 48, 255))
    elif hat == "bobble":
        d.ellipse((cx - 32, head_y - 48, cx + 32, head_y - 8), fill=(48, 110, 186, 255))
        d.ellipse((cx - 8, head_y - 62, cx + 10, head_y - 44), fill=(255, 255, 255, 255))
    elif hat == "crown":
        d.polygon([
            (cx - 30, head_y - 8), (cx - 24, head_y - 42), (cx - 8, head_y - 16),
            (cx, head_y - 48), (cx + 10, head_y - 16), (cx + 24, head_y - 42), (cx + 30, head_y - 8),
        ], fill=(232, 186, 64, 255))
    elif hat == "cowboy":
        d.polygon([(cx - 48, head_y - 8), (cx - 16, head_y - 28), (cx + 16, head_y - 28), (cx + 48, head_y - 8)], fill=(122, 78, 42, 255))
        d.rectangle((cx - 18, head_y - 48, cx + 18, head_y - 16), fill=(122, 78, 42, 255))
    elif hat == "elf":
        d.polygon([(cx - 26, head_y - 14), (cx + 22, head_y - 12), (cx + 36, head_y - 70)], fill=(46, 150, 72, 255))
        d.ellipse((cx + 26, head_y - 80, cx + 46, head_y - 60), fill=(232, 186, 64, 255))
    elif hat == "viking":
        d.polygon([(cx - 26, head_y - 8), (cx - 8, head_y - 40), (cx + 8, head_y - 40), (cx + 26, head_y - 8)], fill=(168, 132, 78, 255))
        d.arc((cx - 40, head_y - 36, cx - 8, head_y + 4), 200, 20, fill=(210, 210, 214, 255), width=4)
        d.arc((cx + 8, head_y - 36, cx + 40, head_y + 4), 160, 340, fill=(210, 210, 214, 255), width=4)
    elif hat == "antlers":
        d.line((cx - 8, head_y - 20, cx - 28, head_y - 58), fill=(122, 78, 42, 255), width=4)
        d.line((cx - 22, head_y - 44, cx - 36, head_y - 52), fill=(122, 78, 42, 255), width=3)
        d.line((cx + 8, head_y - 20, cx + 28, head_y - 58), fill=(122, 78, 42, 255), width=4)
        d.line((cx + 22, head_y - 44, cx + 36, head_y - 52), fill=(122, 78, 42, 255), width=3)
    elif hat == "pirate":
        d.polygon([(cx - 34, head_y - 6), (cx - 10, head_y - 8), (cx + 8, head_y - 36), (cx + 30, head_y - 8)], fill=(32, 32, 36, 255))
        d.polygon([(cx + 4, head_y - 34), (cx + 16, head_y - 34), (cx + 10, head_y - 52)], fill=(196, 40, 48, 255))
    elif hat == "headphones":
        d.arc((cx - 32, head_y - 28, cx + 32, head_y + 16), 200, 340, fill=(32, 32, 36, 255), width=4)
        d.rounded_rectangle((cx - 38, head_y - 8, cx - 26, head_y + 16), radius=4, fill=(32, 32, 36, 255))
        d.rounded_rectangle((cx + 26, head_y - 8, cx + 38, head_y + 16), radius=4, fill=(32, 32, 36, 255))


def feet_point() -> tuple[int, int]:
    return 120, 308
