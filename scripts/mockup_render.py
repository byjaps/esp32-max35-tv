#!/usr/bin/env python3
"""Render 480x320 mockups of the MAX35-TV voice panel screen.

Usa as MESMAS primitivas que o lambda do ESPHome vai usar (quads de triangulos
para os aneis tracejados, anel cheio, linhas radiais, circulos concentricos para
o glow) — o que se ve aqui e o que a placa desenha. Cor em ESPHome nao tem
alpha: tudo o que no canvas original era `globalAlpha` aqui e misturado com o
preto (fundo) antes de escrever o pixel, que da o mesmo resultado.

Since v0.15.5 the screen is minimal: no day of week, no top clock, no date, no
battery footer - and the time sits in the CENTRE of the ring, in white, while
idle. Idle is white (it used to share the cyan of "speaking" and the two states
were indistinguishable on the real panel).

Usage:  python3 mockup_render.py [output.png]
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 480, 320
FONTS = {
    56: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    40: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    28: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    24: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    16: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}

# --- paleta / estado (extraida do HUD eadmin2/jarvis_ai) ---------------------
STATE_STYLE = {
    "standby":   {"speed": 0.15, "color": (0xFF, 0xFF, 0xFF), "glow": 18, "pulse": 0.0},
    "listening": {"speed": 0.50, "color": (0x19, 0xF0, 0xD8), "glow": 30, "pulse": 1.0},
    "thinking":  {"speed": 1.60, "color": (0xFF, 0xB3, 0x00), "glow": 26, "pulse": 0.4},
    "tool":      {"speed": 2.40, "color": (0xFF, 0xB3, 0x00), "glow": 32, "pulse": 0.6},
    "speaking":  {"speed": 0.70, "color": (0x00, 0xE5, 0xFF), "glow": 34, "pulse": 0.8},
    "error":     {"speed": 0.05, "color": (0xFF, 0x4D, 0x5E), "glow": 22, "pulse": 0.0},
}
# "standby" has no label: it shows the clock in the centre (v0.15.5).
LABEL = {"listening": "LISTENING", "thinking": "THINKING",
         "speaking": "SPEAKING", "error": "ERROR", "media": "NOW PLAYING"}
GREEN = (30, 215, 96)


# --- primitivas (espelham o display.h do ESPHome) ----------------------------
def blend(c, a):
    return tuple(max(0, min(255, int(round(v * a)))) for v in c)


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), (0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    # it.filled_rectangle / it.rectangle
    def rect(self, x, y, w, h, color, fill=True):
        if fill:
            self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=color)
        else:
            self.d.rectangle([x, y, x + w - 1, y + h - 1], outline=color)

    # it.line
    def line(self, x0, y0, x1, y1, color):
        self.d.line([x0, y0, x1, y1], fill=color)

    # it.filled_circle
    def circle(self, cx, cy, r, color):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # it.filled_ring  (anel cheio entre r1 e r2)
    def ring(self, cx, cy, r1, r2, color, a=0.0, b=360.0):
        self.arc_quad(cx, cy, r1, r2, a, b, color, steps=max(8, int(abs(b - a) / 3)))

    # segmento de anel desenhado como quads (2 triangulos) — igual ao C++
    def arc_quad(self, cx, cy, r1, r2, a0, a1, color, steps=1, aa=0.0):
        for i in range(steps):
            s = a0 + (a1 - a0) * i / steps
            e = a0 + (a1 - a0) * (i + 1) / steps
            pts = []
            for r, ang in ((r2, s), (r2, e), (r1, e), (r1, s)):
                rad = math.radians(ang - 90 + aa)
                pts.append((cx + math.cos(rad) * r, cy + math.sin(rad) * r))
            self.d.polygon(pts, fill=color)

    # anel tracejado: dash/gap em px de arco, offset em px (como o canvas)
    def dashed_ring(self, cx, cy, r, w, color, alpha, dash_px, gap_px, offset_px):
        c = blend(color, alpha)
        r1, r2 = r - w / 2.0, r + w / 2.0
        circ = 2 * math.pi * r
        period = dash_px + gap_px
        t = (offset_px % period)
        px = -t
        while px < circ:
            d0 = max(px, 0.0)
            d1 = min(px + dash_px, circ)
            if d1 > d0:
                a0 = d0 / circ * 360.0
                a1 = d1 / circ * 360.0
                self.arc_quad(cx, cy, r1, r2, a0, a1, c)
            px += period

    # texto: (x, y) + alinhamento tipo TextAlign do ESPHome
    def text(self, x, y, size, color, align, s):
        f = ImageFont.truetype(FONTS[size], size)
        box = self.d.textbbox((0, 0), s, font=f)
        tw, th = box[2] - box[0], box[3] - box[1]
        if align == "CENTER":
            pos = (x - tw / 2 - box[0], y - th / 2 - box[1])
        elif align == "TOP_LEFT":
            pos = (x - box[0], y - box[1])
        elif align == "TOP_RIGHT":
            pos = (x - tw - box[0], y - box[1])
        elif align == "CENTER_LEFT":
            pos = (x - box[0], y - th / 2 - box[1])
        else:
            pos = (x, y)
        self.d.text(pos, s, font=f, fill=color)
        return tw


# --- o anel ------------------------------------------------------------------
def draw_reactor(c, cx, cy, base, st, rot, level=0.0, t=0.0, sweep=None):
    """Port do drawRing/frame do jarvis-reactor-ring.html.

    sweep=(fraccao, cor) desenha por cima um arco cheio (usado no ecra de media
    para mostrar o VOLUME em vez do anel em espera).
    """
    color = st["color"]
    pulse = 1 + math.sin(t / 300.0) * 0.012 * (1 + st["pulse"] * 3) + level * 0.10
    b = base * pulse
    # 1. anel exterior, solido, quase opaco
    c.ring(cx, cy, b - 1, b + 1, blend(color, 0.9))
    # 2. tracejado fino a rodar
    c.dashed_ring(cx, cy, b * 0.86, 2, color, 0.45, 40, 18, rot * 2)
    # 3. tracejado grosso (muito apagado) a rodar ao contrario
    c.dashed_ring(cx, cy, b * 0.72, 5, color, 0.25, 4, 10, -rot * 3)
    # 4. tracejado medio
    c.dashed_ring(cx, cy, b * 0.58, 2, color, 0.6, 90, 40, rot * 1.2)
    # 5. marcas radiais (60, mais fortes de 5 em 5)
    for i in range(60):
        a = (i / 60.0) * 2 * math.pi + math.radians(rot / 180.0)
        r1 = b * 1.06
        r2 = b * (1.12 if i % 5 == 0 else 1.09)
        c.line(cx + math.cos(a) * r1, cy + math.sin(a) * r1,
               cx + math.cos(a) * r2, cy + math.sin(a) * r2,
               blend(color, 0.8 if i % 5 == 0 else 0.3))
    # 6. nucleo: glow em degraus concentricos (o ESPHome nao tem gradiente)
    gr = b * 0.42
    steps = 10
    for i in range(steps):
        rr = gr * (1 - i / steps)
        c.circle(cx, cy, rr, blend(color, 0.05 + 0.30 * (i / steps) ** 1.6))
    if sweep is not None:
        frac, cor = sweep
        c.arc_quad(cx, cy, b * 0.86 - 3, b * 0.86 + 3, 0, 360 * frac, cor, steps=max(2, int(60 * frac)))
        c.circle(cx, cy, b * 0.42, blend(cor, 0.10))


# --- ecras -------------------------------------------------------------------
def screen_voice(state, rot=140.0, level=0.0, clock="23:47", dia=None, data=None, batt=None):
    """Reproduces the display lambda (v0.15.5): NO day of week, NO top clock, NO
    date and NO battery footer. While idle the centre of the ring shows the TIME
    in white (font_med, 40); the other states show their own word in their color."""
    c = Canvas()
    st = STATE_STYLE[state]
    cx, cy, base = 240, 152, 118
    draw_reactor(c, cx, cy, base, st, rot, level if state == "listening" else 0.0)
    if state == "standby":
        c.text(cx, cy, 40, (255, 255, 255), "CENTER", clock)
    else:
        c.text(cx, cy, 24, st["color"], "CENTER", LABEL[state])
    return c.img


def screen_media(titulo="Noite FM", vol=75, rot=140.0, dia=None, data=None):
    c = Canvas()
    cx, cy, base = 130, 160, 92
    st = STATE_STYLE["standby"]
    draw_reactor(c, cx, cy, base, st, rot, sweep=(vol / 100.0, GREEN))
    c.text(cx, cy, 40, GREEN, "CENTER", "{:.0f}%".format(vol))
    # right column (same coordinates as the lambda)
    c.text(258, 78, 24, GREEN, "TOP_LEFT", "NOW PLAYING")
    c.text(258, 118, 24, (255, 255, 255), "TOP_LEFT", titulo[:18])
    c.text(258, 156, 16, (150, 150, 150), "TOP_LEFT", "volume {:.0f}%".format(vol))
    c.rect(258, 186, 200, 10, (60, 60, 60))
    c.rect(259, 187, int(198 * vol / 100.0), 8, GREEN)
    return c.img


def sheet(cells, cols, path, gap=6, bg=(18, 18, 18)):
    rows = (len(cells) + cols - 1) // cols
    im = Image.new("RGB", (cols * W + (cols + 1) * gap, rows * H + (rows + 1) * gap), bg)
    for i, cell in enumerate(cells):
        r, cc = divmod(i, cols)
        im.paste(cell, (gap + cc * (W + gap), gap + r * (H + gap)))
    im.save(path)
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "preview-painel.png"
    cells = [
        screen_voice("standby"),
        screen_voice("listening", level=0.6),
        screen_voice("thinking"),
        screen_voice("speaking"),
        screen_voice("error"),
        screen_media(),
    ]
    print(sheet(cells, 2, out))
    for i, c in enumerate(cells):
        px = c.load()
        lit = sum(1 for y in range(0, H, 2) for x in range(0, W, 2)
                  if sum(px[x, y]) > 40)
        print("cell", i, "lit pixels:", lit, "/", (W // 2) * (H // 2))
