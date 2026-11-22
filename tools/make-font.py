#!/usr/bin/env python3
"""Build assets/fonts/nebula.ttf: FiraCode Nerd Font Mono + Nebula's own icons, renamed "Nebula Mono".

  python3 tools/make-font.py --base FiraCodeNerdFontMono-Regular.ttf [--out assets/fonts/nebula.ttf]

Get the base from https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip
Needs fontTools (pip install fonttools). Both fonts are SIL OFL 1.1 (see assets/fonts/LICENSE-FONT.md).

Nebula icons live in a free private-use block, so they never clash with Nerd Font glyphs:
  U+E400 logo    U+E401 bolt    U+E402 sparkle   U+E403 prompt   U+E404 face   U+E405 planet
Every shape is a plain polygon, so the build is easy to read and tweak.
"""
import argparse, math
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

ADV = 1200            # FiraCode Nerd *Mono* cell width (1950 units per em)
CX, CY = 600, 620     # visual centre of an icon cell


def area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def cw(p):            # TrueType fills clockwise outlines
    return p if area(p) < 0 else p[::-1]


def ccw(p):           # ...and cuts holes counter-clockwise
    return p if area(p) > 0 else p[::-1]


def ellipse(cx, cy, rx, ry, rot=0.0, n=72):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def circle(cx, cy, r): return ellipse(cx, cy, r, r)


def ring(cx, cy, ro, ri, rx_scale=1.0, rot=0.0):
    return [cw(ellipse(cx, cy, ro * rx_scale, ro, rot)), ccw(ellipse(cx, cy, ri * rx_scale, ri, rot))]


def star(cx, cy, ro, ri, points=4, rot=90):
    pts = []
    for i in range(points * 2):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + 180.0 * i / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def arc_band(cx, cy, r_out, r_in, a0, a1, n=24):
    outer = [(cx + r_out * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r_out * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    inner = [(cx + r_in * math.cos(math.radians(a1 - (a1 - a0) * i / n)), cy + r_in * math.sin(math.radians(a1 - (a1 - a0) * i / n))) for i in range(n + 1)]
    return outer + inner


def logo():           # a nebula: ring, bright core, one orbiting spark
    o = math.radians(38)
    return ring(CX, CY, 600, 460) + [cw(circle(CX, CY, 230)), cw(circle(CX + 600 * math.cos(o), CY + 600 * math.sin(o), 140))]


def bolt():
    return [cw([(720, 1480), (240, 640), (540, 640), (430, -180), (960, 820), (660, 820), (820, 1480)])]


def sparkle():
    return [cw(star(470, 560, 520, 130)), cw(star(930, 1170, 270, 70))]


def prompt():
    return [cw([(160, 1260), (400, 1260), (1040, 640), (400, 20), (160, 20), (800, 640)])]


def face():
    return ring(CX, CY, 620, 500) + [cw(circle(430, 760, 85)), cw(circle(770, 760, 85)), cw(arc_band(CX, 720, 330, 235, 205, 335))]


def planet():
    return [cw(circle(CX, CY, 290))] + ring(CX, CY, 640, 520, rx_scale=1.0, rot=0.0)[:0] + \
        [cw(ellipse(CX, CY, 600, 170, 24)), ccw(ellipse(CX, CY, 500, 95, 24))]


ICONS = [(0xE400, "nebula.logo", logo), (0xE401, "nebula.bolt", bolt), (0xE402, "nebula.sparkle", sparkle),
         (0xE403, "nebula.prompt", prompt), (0xE404, "nebula.face", face), (0xE405, "nebula.planet", planet)]


def make_glyph(contours, glyf):
    pen = TTGlyphPen(None)
    for c in contours:
        pts = [(round(x), round(y)) for x, y in c]
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    g = pen.glyph()
    g.recalcBounds(glyf)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", default="assets/fonts/nebula.ttf")
    a = ap.parse_args()
    font = TTFont(a.base)
    glyf, hmtx, order = font["glyf"], font["hmtx"], list(font.getGlyphOrder())
    assert all(font["hmtx"]["A"][0] == ADV for _ in [0]), "base font is not the Nerd *Mono* variant"
    for cp, name, fn in ICONS:
        g = make_glyph(fn(), glyf)
        glyf[name] = g
        hmtx[name] = (ADV, g.xMin)
        order.append(name)
        for t in font["cmap"].tables:
            if t.isUnicode() and (cp <= 0xFFFF or t.format == 12):
                t.cmap[cp] = name
    font.setGlyphOrder(order)
    # rename: it is a new family now
    fam, ps = "Nebula Mono", "NebulaMono-Regular"
    for n in font["name"].names:
        if n.nameID in (1, 16): n.string = fam
        elif n.nameID in (2, 17): n.string = "Regular"
        elif n.nameID == 3: n.string = "J.I.T.E.T.E.E.;NebulaMono-Regular;1.0"
        elif n.nameID == 4: n.string = fam
        elif n.nameID == 6: n.string = ps
        elif n.nameID == 0: n.string = str(n.toUnicode()) + " | Nebula icons: Copyright 2026 J.I.T.E.T.E.E."
    font.save(a.out)
    print("wrote", a.out, "with", len(ICONS), "Nebula icons at U+E400..U+E%03X" % (0x400 + len(ICONS) - 1))


if __name__ == "__main__":
    main()
