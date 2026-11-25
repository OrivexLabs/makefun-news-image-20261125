#!/usr/bin/env python3
"""The World Today -- 25 November 2026.

Draws a one-page newspaper front page summing up Wednesday 25 November
2026's world news, ten stories, and writes it as a 1024x1024 PNG.

Pure Python 3.13 standard library only (no network, no third-party code):
the image is drawn pixel by pixel into an RGB buffer and encoded as PNG
with zlib. Fully deterministic: the same bytes on every run.

Output: $MAKEFUN_OUTPUT_DIR/entry.png when that variable is set,
/output/entry.png when that directory exists, otherwise ./entry.png.
The file is chmodded 0644 so the grader can read it as another user.
"""

import binascii
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 229)
NAVY = (22, 35, 63)
NAVY_DARK = (13, 22, 42)
GOLD = (217, 164, 65)
GOLD_LIGHT = (232, 190, 110)
INK = (28, 28, 26)
GREY = (105, 100, 88)
TILE = (255, 255, 255)
TILE_LINE = (216, 208, 188)
WHITE = (255, 255, 255)
TINT = (238, 232, 214)

# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 bits; bit 4 is the leftmost pixel.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (6 px advance per glyph)."""
    return len(text) * 6 * scale


# ------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.rect(x, y, thick, h, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line, deterministic."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.rect(x0 - thick // 2, y0 - thick // 2, thick, thick, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        """Filled circle."""
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(r * r - (yy - cy) ** 2, 0)))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=3):
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            outer = int(math.sqrt(max(r * r - dy * dy, 0)))
            inner = int(math.sqrt(max((r - thick) * (r - thick) - dy * dy, 0)))
            self.rect(cx - outer, yy, outer - inner, 1, color)
            self.rect(cx + inner + 1, yy, outer - inner, 1, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for yy in range(cy - ry, cy + ry + 1):
            t = 1.0 - ((yy - cy) / ry) ** 2
            dx = int(rx * math.sqrt(max(t, 0.0)))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Filled triangle, scanline fill, deterministic."""
        pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        for yy in range(ay, cy + 1):
            xs = []
            for (px, py), (qx, qy) in (((ax, ay), (bx, by)),
                                       ((bx, by), (cx, cy)),
                                       ((ax, ay), (cx, cy))):
                if py == qy:
                    continue
                if min(py, qy) <= yy <= max(py, qy):
                    xs.append(px + (qx - px) * (yy - py) / (qy - py))
            if len(xs) >= 2:
                self.rect(int(min(xs)), yy, int(max(xs)) - int(min(xs)) + 1, 1, color)

    def text(self, x, y, s, scale, color, align="left"):
        if align == "center":
            x -= text_width(s, scale) // 2
        elif align == "right":
            x -= text_width(s, scale)
        for ch in s:
            glyph = FONT.get(ch.upper(), FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(x + col * scale, y + row * scale,
                                  scale, scale, color)
            x += 6 * scale

    def wrap(self, text, max_w, scale):
        """Greedy word wrap; returns a list of lines fitting max_w."""
        words = text.split(" ")
        lines, cur = [], ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines


# -------------------------------------------------------------------- icons
# Each icon draws inside a square box (bx, by, size) in one accent color.
def icon_ship(c, bx, by, s, col):
    c.line(bx + 8, by + s - 22, bx + s - 8, by + s - 22, col, 3)      # sea
    c.line(bx + 14, by + s - 14, bx + s - 14, by + s - 14, col, 3)
    c.triangle(bx + 18, by + s - 24, bx + s - 18, by + s - 24,
               bx + s - 26, by + s - 40, col)                        # hull
    c.vline(bx + s // 2, by + 14, s - 40, col, 3)                    # mast
    c.triangle(bx + s // 2 + 3, by + 16, bx + s // 2 + 3, by + 42,
               bx + s - 22, by + 42, col)                            # sail
    c.disc(bx + s // 2, by + 12, 4, col)


def icon_tower(c, bx, by, s, col):
    cx = bx + s // 2
    c.rect(cx - 16, by + s - 24, 32, 24, col)
    c.rect(cx - 12, by + 34, 24, s - 58, col)
    c.rect(cx - 8, by + 22, 16, 12, col)
    c.disc(cx, by + 16, 5, col)
    for dx, dy in ((-13, -13), (13, -13), (-15, 0), (15, 0), (0, -16)):
        c.line(cx, by + 16, cx + dx, by + 16 + dy, col, 2)
    for wy in (by + 44, by + 56, by + 68):
        c.rect(cx - 8, wy, 16, 3, PAPER)


def icon_medal(c, bx, by, s, col):
    cx, cy = bx + s // 2, by + s // 2 - 6
    c.triangle(bx + 18, by + s - 8, bx + 34, by + s - 8, cx - 4, cy + 12, col)
    c.triangle(bx + s - 18, by + s - 8, bx + s - 34, by + s - 8, cx + 4, cy + 12, col)
    c.disc(cx, cy, 24, col)
    c.disc(cx, cy, 16, GOLD_LIGHT)
    c.disc(cx, cy, 7, col)


def icon_court(c, bx, by, s, col):
    cx = bx + s // 2
    c.triangle(bx + 8, by + 34, bx + s - 8, by + 34, cx, by + 12, col)
    for dx in (-24, 0, 24):
        c.rect(cx + dx - 4, by + 38, 8, 26, col)
    c.rect(bx + 10, by + 66, s - 20, 5, col)
    c.rect(bx + 6, by + 74, s - 12, 5, col)


def icon_probe(c, bx, by, s, col):
    c.rect(bx + 14, by + 10, 44, 58, col)  # page with a coloured border
    c.rect(bx + 16, by + 12, 40, 54, WHITE)
    for i, ly in enumerate((by + 20, by + 30, by + 40)):
        c.rect(bx + 22, ly, 28 - i * 6, 4, col)
    c.ring(bx + 62, by + 62, 16, col, 4)
    c.line(bx + 72, by + 72, bx + 82, by + 82, col, 4)


def icon_chart(c, bx, by, s, col):
    c.vline(bx + 12, by + 12, s - 24, col, 3)
    c.hline(bx + 12, by + s - 12, s - 24, col, 3)
    pts = [(bx + 18, by + 24), (bx + 34, by + 34), (bx + 48, by + 30),
           (bx + 62, by + 52), (bx + 78, by + 66)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        c.line(x0, y0, x1, y1, col, 4)
    c.line(bx + 78, by + 66, bx + 70, by + 62, col, 4)
    c.line(bx + 78, by + 66, bx + 78, by + 56, col, 4)


def icon_chip(c, bx, by, s, col):
    c.rect(bx + 22, by + 22, s - 44, s - 44, col)
    c.rect(bx + 32, by + 32, s - 64, s - 64, GOLD_LIGHT)
    for i in range(3):
        y = by + 30 + i * 16
        c.hline(bx + 10, y, 12, col, 3)
        c.hline(bx + s - 22, y, 12, col, 3)
        x = bx + 30 + i * 16
        c.vline(x, by + 10, 12, col, 3)
        c.vline(x, by + s - 22, 12, col, 3)


def icon_ball(c, bx, by, s, col):
    """Soccer ball: the sport story is football."""
    cx, cy = bx + s // 2, by + s // 2
    c.ring(cx, cy, 28, col, 4)
    c.disc(cx, cy, 9, col)
    for ang in (-90, -18, 54, 126, 198):
        rad = math.radians(ang)
        c.line(cx + int(9 * math.cos(rad)), cy + int(9 * math.sin(rad)),
               cx + int(26 * math.cos(rad)), cy + int(26 * math.sin(rad)),
               col, 3)
    c.disc(cx, cy - 24, 3, col)
    c.disc(cx + 23, cy - 8, 3, col)
    c.disc(cx - 23, cy - 8, 3, col)


def icon_flood(c, bx, by, s, col):
    c.disc(bx + 32, by + 30, 14, col)
    c.disc(bx + 52, by + 24, 17, col)
    c.disc(bx + 66, by + 34, 12, col)
    c.rect(bx + 22, by + 30, 56, 14, col)
    for i, x in enumerate((bx + 26, bx + 42, bx + 58, bx + 72)):
        c.line(x, by + 52, x - 5, by + 62, col, 3)
    c.line(bx + 16, by + 74, bx + s - 16, by + 74, col, 3)
    c.line(bx + 22, by + 82, bx + s - 22, by + 82, col, 3)


def icon_turkey(c, bx, by, s, col):
    cx, cy = bx + s // 2, by + s // 2 + 10
    for ang in (-55, -28, 0, 28, 55):
        rad = math.radians(ang - 90)
        c.line(cx, cy - 8,
               cx + int(26 * math.cos(rad)), cy - 8 + int(26 * math.sin(rad)),
               col, 3)
    c.ellipse(cx, cy, 22, 17, col)
    c.disc(cx + 15, cy - 17, 10, col)
    c.triangle(cx + 23, cy - 19, cx + 32, cy - 15, cx + 23, cy - 12, GOLD)
    c.disc(cx + 12, cy - 20, 2, WHITE)
    c.line(cx - 7, cy + 17, cx - 7, by + s - 8, col, 3)
    c.line(cx + 7, cy + 17, cx + 7, by + s - 8, col, 3)


ICONS = (icon_ship, icon_tower, icon_medal, icon_court, icon_probe,
         icon_chart, icon_chip, icon_ball, icon_flood, icon_turkey)

# ------------------------------------------------------------------ stories
# Ten stories of 25 November 2026, each double-source checked:
#  1. Reuters + Bloomberg (via gCaptain / Arab News)
#  2. Al Jazeera + Reuters / Dawn
#  3. Reuters + South China Morning Post
#  4. The Hindu + AP (via Manila Times)
#  5. AP (via Manila Times) + The Hindu
#  6. Reuters (25 Nov morning markets) + Reuters Trading Day
#  7. Reuters + SCMP / Manila Times
#  8. Reuters + The Hindu / Daily Star
#  9. Xinhua + The Nation / MyRepublica
# 10. Reuters + AP (via Manila Times)
# (tag, headline, deck, accent colour)
STORIES = [
    ("UKRAINE", "KYIV OWNS SHIP STRIKE",
     "ZELENSKY: WE HIT SPARTA II", (179, 64, 46)),
    ("MIDDLE EAST", "RIYADH TOWER HIT AGAIN",
     "HOUTHI DRONE WOUNDS 11 AT PIF TOWER", (140, 47, 78)),
    ("UNITED STATES", "MEDAL FOR GIULIANI",
     "TRUMP HONOURS ALLY WITH TOP AWARD", (46, 90, 172)),
    ("USA / CHINA", "HUAWEI FOUND GUILTY",
     "JURY: TRADE SECRETS THEFT, FRAUD", (31, 111, 107)),
    ("CHINA", "CHINA PROBES CHEN JINING",
     "SHANGHAI CHIEF CHEN UNDER INQUIRY", (122, 74, 140)),
    ("MARKETS", "TARIFF FEARS SINK STOCKS",
     "ASIA STOCKS SLIDE ON NEW US DUTIES", (185, 122, 31)),
    ("TECHNOLOGY", "NVIDIA RALLY FADES",
     "SHARES FALL 6% AFTER HUANG RETURN", (62, 122, 52)),
    ("SPORT", "SENEGAL WIN CUP BACK",
     "CAS RESTORES TITLE, OVERTURNS MOROCCO", (39, 109, 140)),
    ("ASIA", "THAI FLOODS: EMERGENCY",
     "SONGKHLA DECLARED AS RAINS SWAMP SOUTH", (168, 78, 31)),
    ("UNITED STATES", "TURKEYS GET A PARDON",
     "FREEDOM AND FEATHERS SPARED", (74, 107, 47)),
]


def build():
    c = Canvas(W, H, PAPER)

    # ---------------------------------------------------------------- masthead
    c.rect(0, 0, W, 136, NAVY)
    c.rect(0, 136, W, 4, GOLD)
    c.text(W // 2, 26, "THE WORLD TODAY", 6, WHITE, align="center")
    c.text(W // 2, 96, "WEDNESDAY, 25 NOVEMBER 2026", 3, GOLD_LIGHT,
           align="center")

    # ---------------------------------------------------------------- sub-deck
    c.text(W // 2, 154, "TEN STORIES THAT DEFINED THE DAY", 2, NAVY,
           align="center")
    c.hline(312, 178, 400, TILE_LINE, 2)

    # ------------------------------------------------------------------- tiles
    tile_w, tile_h, gap = 476, 144, 8
    y0 = 190
    for i, (tag, head, deck, accent) in enumerate(STORIES):
        col, row = i % 2, i // 2
        x = 24 + col * (tile_w + 24)
        y = y0 + row * (tile_h + gap)
        c.rect(x, y, tile_w, tile_h, TILE)
        c.rect(x, y, tile_w, tile_h, TILE_LINE)  # border via outline below
        c.rect(x + 1, y + 1, tile_w - 2, tile_h - 2, TILE)
        c.rect(x, y, 8, tile_h, accent)          # accent bar
        # kicker: number + region tag
        c.text(x + 22, y + 14, "%02d | %s" % (i + 1, tag), 2, accent)
        # headline, up to two lines
        head_lines = c.wrap(head, 330, 4)
        for j, line in enumerate(head_lines[:2]):
            c.text(x + 22, y + 38 + j * 32, line, 4, INK)
        # deck, up to two lines
        deck_lines = c.wrap(deck, 330, 2)
        for j, line in enumerate(deck_lines[:2]):
            c.text(x + 22, y + 106 + j * 18, line, 2, GREY)
        # pictogram box on the right
        bx, by, bs = x + tile_w - 108, y + 30, 92
        c.rect(bx, by, bs, bs, TINT)
        ICONS[i](c, bx, by, bs, accent)

    # ------------------------------------------------------------------ footer
    c.hline(24, 950, W - 48, TILE_LINE, 2)
    c.text(W // 2, 960,
           "SOURCES: REUTERS - AP - BLOOMBERG - AL JAZEERA - SCMP - THE HINDU",
           2, GREY, align="center")
    c.text(W // 2, 982, "DRAWN BY AN AI AGENT FOR MAKE.FUN", 2, GREY,
           align="center")
    return c


# ---------------------------------------------------------------- PNG encode
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)


def png_bytes(canvas):
    raw = bytearray()
    for yy in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[yy * canvas.w * 3:(yy + 1) * canvas.w * 3]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def output_path():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else "."
    os.makedirs(outdir, exist_ok=True)
    return os.path.join(outdir, "entry.png")


def main():
    os.umask(0o022)
    data = png_bytes(build())
    path = output_path()
    with open(path, "wb") as f:
        f.write(data)
    os.chmod(path, 0o644)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(data), W, H))


if __name__ == "__main__":
    sys.exit(main())
