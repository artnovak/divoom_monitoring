from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw

from .metrics import PcMetrics


RGB = tuple[int, int, int]
BLACK: RGB = (2, 3, 7)
DIM: RGB = (10, 12, 18)
WHITE: RGB = (230, 244, 255)
CYAN: RGB = (0, 222, 255)
MAGENTA: RGB = (255, 67, 184)
GREEN: RGB = (58, 255, 125)
AMBER: RGB = (255, 190, 52)
RED: RGB = (255, 58, 78)
BLUE: RGB = (42, 161, 255)


FONT_3X5 = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "%": ("101", "001", "010", "100", "101"),
    "C": ("111", "100", "100", "100", "111"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("111", "100", "101", "101", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "111"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "O": ("111", "101", "101", "101", "111"),
    "Q": ("111", "101", "101", "111", "001"),
    "R": ("110", "101", "110", "101", "101"),
    "D": ("110", "101", "101", "101", "110"),
    "N": ("101", "111", "111", "111", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "M": ("101", "111", "111", "101", "101"),
    "P": ("110", "101", "110", "100", "100"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
}


def clamp_percent(value: float | None) -> int:
    if value is None:
        return 0
    return max(0, min(100, int(round(value))))


def color_for_percent(value: float | None, cool: RGB = CYAN) -> RGB:
    percent = clamp_percent(value)
    if percent >= 88:
        return RED
    if percent >= 68:
        return AMBER
    return cool


def text3(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: RGB) -> None:
    x, y = xy
    for char in text.upper():
        glyph = FONT_3X5.get(char)
        if not glyph:
            x += 2
            continue
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    draw.point((x + col, y + row), fill)
        x += 4


def _dim(color: RGB, amount: int = 95) -> RGB:
    return tuple(max(0, channel - amount) for channel in color)


def render_value_screen(label: str, value: float | None, color: RGB, tick: int) -> Image.Image:
    img = Image.new("RGB", (16, 16), BLACK)
    draw = ImageDraw.Draw(img)
    percent = clamp_percent(value)
    color = color_for_percent(value, color)

    label_x = max(0, (16 - (len(label) * 4 - 1)) // 2)
    text3(draw, (label_x, 0), label, color)

    value_text = f"{percent:02d}%" if percent < 100 else "100"
    value_x = max(0, (16 - (len(value_text) * 4 - 1)) // 2)
    text3(draw, (value_x, 7), value_text, WHITE)

    bar_width = round(percent / 100 * 16)
    draw.rectangle((0, 14, 15, 15), fill=DIM)
    if bar_width:
        draw.rectangle((0, 14, bar_width - 1, 15), fill=color)
    return img


def render_net_screen(metrics: PcMetrics, tick: int) -> Image.Image:
    img = Image.new("RGB", (16, 16), BLACK)
    draw = ImageDraw.Draw(img)
    speed = max(metrics.net_down_kbps, metrics.net_up_kbps)
    scaled = min(15, int(math.log10(speed + 1) * 4))

    text3(draw, (0, 0), "N", BLUE)
    draw.line((6, 2, 8, 0, 10, 2), fill=GREEN)
    draw.line((8, 0, 8, 5), fill=GREEN)
    draw.line((11, 3, 13, 5, 15, 3), fill=AMBER)
    draw.line((13, 0, 13, 5), fill=AMBER)

    for x in range(16):
        wave = int((math.sin((x + tick) / 2.0) + 1) * 2)
        h = max(1, min(8, scaled - abs(8 - x) // 2 + wave))
        color = BLUE if x % 2 else CYAN
        draw.line((x, 15, x, 15 - h), fill=color)
    return img


def render_telegram(sender: str, count: int, tick: int) -> Image.Image:
    img = Image.new("RGB", (16, 16), (0, 18, 40))
    draw = ImageDraw.Draw(img)
    blink = WHITE if tick % 2 == 0 else BLUE

    draw.polygon([(2, 7), (14, 2), (10, 14), (7, 10), (4, 12)], fill=BLUE)
    draw.line((7, 10, 14, 2), fill=WHITE)
    draw.point((8, 11), fill=(0, 85, 155))

    initials = "".join(ch for ch in sender.upper() if ch.isalnum())[:1] or "T"
    text3(draw, (0, 0), initials, blink)
    if count > 1:
        badge = str(min(9, count))
        draw.rectangle((11, 11, 15, 15), fill=RED)
        text3(draw, (12, 10), badge, WHITE)
    return img


def _short_code(text: str, fallback: str, length: int = 3) -> str:
    letters = "".join(ch for ch in text.upper() if "A" <= ch <= "Z" or ch.isdigit())
    if not letters:
        return fallback
    return letters[:length]


def _format_time(seconds: int | None) -> str:
    if seconds is None:
        return "ON"
    minutes = max(0, seconds // 60)
    if minutes >= 100:
        return "99M"
    return f"{minutes:02d}M"


def _center_x(text: str) -> int:
    return max(0, (16 - (len(text) * 4 - 1)) // 2)


def render_game(
    kind: str,
    title: str,
    subtitle: str = "",
    elapsed_seconds: int | None = None,
    tick: int = 0,
    mode: str = "",
    champion: str = "",
    kills: int | None = None,
    deaths: int | None = None,
    assists: int | None = None,
) -> Image.Image:
    if kind == "lol":
        screen = (tick // 4) % 3
        if screen == 1:
            return render_lol_mode(mode, champion or subtitle, elapsed_seconds, tick)
        if screen == 2:
            return render_lol_score(kills, deaths, assists, tick)
        return render_lol_summary(subtitle, elapsed_seconds, tick)
    return render_steam_game(title, subtitle, elapsed_seconds, tick)


def render_lol_summary(subtitle: str, elapsed_seconds: int | None, tick: int) -> Image.Image:
    main = "LOL"
    color = (0, 182, 255)
    accent = (255, 211, 92)
    bg = (1, 8, 20)
    img = Image.new("RGB", (16, 16), bg)
    draw = ImageDraw.Draw(img)

    text3(draw, (2, 0), main, color)
    code = _short_code(subtitle, "RUN")
    text3(draw, (_center_x(code), 6), code, WHITE)

    footer = _format_time(elapsed_seconds)
    text3(draw, (_center_x(footer), 11), footer, accent)

    return img


def render_lol_mode(mode: str, champion: str, elapsed_seconds: int | None, tick: int) -> Image.Image:
    img = Image.new("RGB", (16, 16), (1, 8, 20))
    draw = ImageDraw.Draw(img)
    mode_code = _short_code(mode, "LIVE", length=4)
    champ_code = _short_code(champion, "CHMP", length=4)
    time_code = _format_time(elapsed_seconds)

    text3(draw, (_center_x(mode_code), 0), mode_code, (255, 211, 92))
    text3(draw, (_center_x(champ_code), 6), champ_code, WHITE)
    text3(draw, (_center_x(time_code), 11), time_code, (0, 182, 255))

    return img


def render_lol_score(kills: int | None, deaths: int | None, assists: int | None, tick: int) -> Image.Image:
    img = Image.new("RGB", (16, 16), (1, 8, 20))
    draw = ImageDraw.Draw(img)

    rows = [
        ("K", kills, (72, 255, 132)),
        ("D", deaths, (255, 58, 78)),
        ("A", assists, (0, 182, 255)),
    ]
    for y, (label, value, color) in zip((0, 5, 10), rows):
        number = 0 if value is None else max(0, min(99, value))
        text3(draw, (0, y), f"{label}{number:02d}", color)
    return img


def _scroll_text(draw: ImageDraw.ImageDraw, text: str, y: int, fill: RGB, tick: int) -> None:
    letters = "".join(ch for ch in text.upper() if "A" <= ch <= "Z" or ch.isdigit())
    letters = letters or "GAME"
    padded = "  " + letters + "  "
    width = len(padded) * 4
    offset = tick % max(1, width)
    x = 4 - offset
    for char in padded:
        text3(draw, (x, y), char, fill)
        x += 4


def render_steam_game(title: str, subtitle: str, elapsed_seconds: int | None, tick: int) -> Image.Image:
    color = (94, 172, 255)
    accent = (130, 255, 170)
    bg = (3, 7, 14)
    img = Image.new("RGB", (16, 16), bg)
    draw = ImageDraw.Draw(img)

    screen = (tick // 8) % 3
    if screen == 2 and elapsed_seconds is not None:
        text3(draw, (_center_x("PLAY"), 0), "PLAY", color)
        text3(draw, (_center_x(_format_time(elapsed_seconds)), 7), _format_time(elapsed_seconds), accent)
        return img

    text3(draw, (_center_x("STE"), 0), "STE", color)
    text3(draw, (_center_x("AM"), 5), "AM", color)
    _scroll_text(draw, subtitle, 11, accent, tick)

    return img


@dataclass(slots=True)
class DashboardRenderer:
    screen_seconds: float = 4.0

    def render(self, metrics: PcMetrics, tick: int, now: float) -> Image.Image:
        screen = int(now / self.screen_seconds) % 3
        if screen == 0:
            return render_value_screen("CPU", metrics.cpu, CYAN, tick)
        if screen == 1:
            gpu_value = metrics.gpu if metrics.gpu is not None else metrics.disk
            return render_value_screen("GPU", gpu_value, GREEN, tick)
        return render_value_screen("RAM", metrics.ram, MAGENTA, tick)
