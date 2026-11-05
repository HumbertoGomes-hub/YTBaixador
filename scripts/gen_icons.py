#!/usr/bin/env python3
"""Gera os ícones PNG da extensão (quadrado vermelho arredondado com seta de download).

    python3 scripts/gen_icons.py

Só usa a biblioteca padrão. Grava extension/icons/icon{16,48,128}.png.
"""

import struct
import zlib

from common import EXTENSION

RED = (204, 0, 0)
WHITE = (255, 255, 255)
SUPERSAMPLE = 4


def inside_rounded_square(x, y, n, r):
    cx = min(max(x, r), n - r)
    cy = min(max(y, r), n - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def inside_arrow(u, v):
    if 0.43 <= u <= 0.57 and 0.20 <= v <= 0.52:  # haste
        return True
    if 0.40 <= v <= 0.64 and abs(u - 0.5) <= (0.64 - v) * 1.15:  # ponta
        return True
    return 0.24 <= u <= 0.76 and 0.72 <= v <= 0.80  # base


def render(size):
    n = size * SUPERSAMPLE
    radius = n * 0.22
    rows = []
    for py in range(size):
        row = bytearray([0])  # filtro PNG "None"
        for px in range(size):
            r = g = b = covered = 0
            for sy in range(SUPERSAMPLE):
                for sx in range(SUPERSAMPLE):
                    x = px * SUPERSAMPLE + sx + 0.5
                    y = py * SUPERSAMPLE + sy + 0.5
                    if inside_rounded_square(x, y, n, radius):
                        c = WHITE if inside_arrow(x / n, y / n) else RED
                        r, g, b, covered = r + c[0], g + c[1], b + c[2], covered + 1
            if covered:
                row += bytes((round(r / covered), round(g / covered), round(b / covered),
                              round(255 * covered / SUPERSAMPLE**2)))
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))
    return b"".join(rows)


def png(size, pixels):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA 8 bits
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = EXTENSION / "icons"
    out.mkdir(exist_ok=True)
    for size in (16, 48, 128):
        path = out / f"icon{size}.png"
        path.write_bytes(png(size, render(size)))
        print(f"✓ {path.relative_to(EXTENSION.parent)}")
