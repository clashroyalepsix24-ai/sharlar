#!/usr/bin/env python3
# Pure-stdlib PNG icon generator for the Sharlar Saralash PWA.
import os, zlib, struct

OUT = os.path.expanduser("~/sharlar-app")
os.makedirs(OUT, exist_ok=True)

TOP   = (0x24, 0x2a, 0x52)   # bg gradient top
BOT   = (0x0d, 0x0f, 0x22)   # bg gradient bottom
GLASS = (0x45, 0x4c, 0x78)   # tube glass tint
BORDER= (0xd6, 0xdc, 0xff)   # tube rim
WHITE = (255, 255, 255)
# balls bottom -> top: red, yellow, green, blue (matches game palette)
BALLS = [(0xef, 0x47, 0x6f), (0xff, 0xd1, 0x66), (0x06, 0xd6, 0xa0), (0x4d, 0x8c, 0xff)]

def lerp(a, b, t): return a + (b - a) * t
def mix(c1, c2, t):
    return (int(round(lerp(c1[0], c2[0], t))),
            int(round(lerp(c1[1], c2[1], t))),
            int(round(lerp(c1[2], c2[2], t))))

def render(size, mode):
    # mode: 'rounded' (transparent rounded corners), 'square' (opaque full square),
    #       'maskable' (opaque full square, art inside safe zone)
    SS = 3 if size <= 200 else 2
    S = size * SS
    buf = bytearray(S * S * 4)

    R = S * 0.225 if mode == "rounded" else 0.0
    art = 0.80 if mode == "maskable" else 1.0     # shrink art for maskable safe zone
    cx = S / 2.0
    cw = S * 0.34 * art
    cr = cw / 2.0
    mid = S * 0.5
    half_h = S * 0.34 * art
    top = mid - half_h
    bot = mid + half_h

    n = 3
    bd = cw * 0.80
    br = bd / 2.0
    gap = bd * 0.92
    centers = []
    yy = bot - (S * 0.055 * art) - br
    for i in range(n):
        centers.append(yy)
        yy -= gap

    def in_round_sq(x, y):
        if mode != "rounded":
            return True
        rx = x if x < S - 1 - x else S - 1 - x
        ry = y if y < S - 1 - y else S - 1 - y
        if rx >= R or ry >= R:
            return True
        dx = R - rx; dy = R - ry
        return dx * dx + dy * dy <= R * R

    edge = 2.2 * SS
    for y in range(S):
        t = y / (S - 1)
        bg = mix(TOP, BOT, t)
        row = y * S * 4
        cyc = top if y < top else (bot if y > bot else y)   # clamp for pill dist
        for x in range(S):
            i = row + x * 4
            if not in_round_sq(x, y):
                buf[i + 3] = 0
                continue
            r, g, b = bg
            # tube (pill) glass
            dxc = x - cx
            d = (dxc * dxc + (y - cyc) * (y - cyc)) ** 0.5
            if d <= cr:
                r, g, b = mix(bg, GLASS, 0.55)
                if d > cr - edge:
                    r, g, b = mix((r, g, b), BORDER, 0.55)
            # balls
            for ci in range(n):
                cyv = centers[ci]
                dx = x - cx; dy = y - cyv
                if dx * dx + dy * dy <= br * br:
                    col = BALLS[ci]
                    hx = cx - 0.34 * br; hy = cyv - 0.36 * br
                    hd = (((x - hx) ** 2 + (y - hy) ** 2) ** 0.5) / (br * 1.15)
                    hl = 1 - hd
                    if hl < 0: hl = 0
                    col = mix(col, WHITE, min(0.85, hl * hl * 0.9))
                    sh = dy / br
                    if sh > 0:
                        col = mix(col, (0, 0, 0), sh * 0.22)
                    r, g, b = col
                    break
            buf[i] = r; buf[i + 1] = g; buf[i + 2] = b; buf[i + 3] = 255

    # downsample SSxSS with premultiplied averaging
    out = bytearray(size * size * 4)
    cnt = SS * SS
    for oy in range(size):
        for ox in range(size):
            Rr = Gg = Bb = Aa = 0
            for sy in range(SS):
                base = (oy * SS + sy) * S * 4
                for sx in range(SS):
                    j = base + (ox * SS + sx) * 4
                    a = buf[j + 3]
                    Rr += buf[j] * a; Gg += buf[j + 1] * a; Bb += buf[j + 2] * a; Aa += a
            oi = (oy * size + ox) * 4
            if Aa == 0:
                out[oi] = out[oi + 1] = out[oi + 2] = out[oi + 3] = 0
            else:
                out[oi] = Rr // Aa; out[oi + 1] = Gg // Aa; out[oi + 2] = Bb // Aa
                out[oi + 3] = Aa // cnt
    return bytes(out), size

def write_png(path, rgba, size):
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))
    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))

jobs = [
    ("icon-192.png",           192, "rounded"),
    ("icon-512.png",           512, "rounded"),
    ("icon-192-maskable.png",  192, "maskable"),
    ("icon-512-maskable.png",  512, "maskable"),
    ("apple-touch-icon.png",   180, "square"),
    ("favicon-64.png",          64, "rounded"),
]
for name, size, mode in jobs:
    rgba, s = render(size, mode)
    write_png(os.path.join(OUT, name), rgba, s)
    print("wrote", name)
print("done ->", OUT)
