"""Generates the `lvgl:` section of the robot face from the Jarvis manifest (v1.0).

Why a generator: it is ~100 widgets whose coordinates are measured in the manifest; so
the coordinates live in a single place and the YAML always comes out the same.

Lessons from the panel (29/10) that this file already takes into account:
  * LVGL `arc` and `line` come out GREY on the device → everything is `obj`;
  * crescents (mouth, eyebrows, waves) = full ellipse + ellipse in the background colour;
  * ABSOLUTE coordinates inside transparent 480x320 groups at (0,0) with
    `pad_all: 0` (relative ones inside small boxes came out shifted);
  * `scroll_dir: NONE` + `scrollbar_mode: "OFF"` (the trunk goes off-screen and LVGL
    showed the scrollbar on the right).
"""
import os
import math

M = {
    "casca": (120, 75, 240, 210, 80),
    "viseira": (150, 122, 180, 130, 56),
    "orelha_e": (104, 178, 22, 46, 11),
    "orelha_d": (354, 178, 22, 46, 11),
    "led_e": (110, 196, 10, 10, 50),
    "led_d": (365, 196, 10, 10, 50),
    "antena": (237, 40, 7, 42, 3),
    "led_antena": (231, 22, 18, 18, 50),
    "pescoco": (222, 268, 36, 34, 10),
    "tronco": (110, 290, 260, 92, 52),
    "sobrancelha_e": (183, 141, 38, 18, 50),
    "sobrancelha_d": (259, 141, 38, 18, 50),
}

FUNDO = "0x05080C"
VISEIRA = "0x090E15"
CIANO = "0x40E0FF"
VERMELHO = "0xFF6060"
TEXTO = "0x96A8BE"

L = []


def grupo(ident, ind, **props):
    p = " " * (ind + 4)
    L.append(" " * ind + "- obj:")
    L.append(f"{p}id: {ident}")
    L.append(f"{p}x: 0")
    L.append(f"{p}y: 0")
    L.append(f"{p}width: 480")
    L.append(f"{p}height: 320")
    L.append(f"{p}pad_all: 0")
    L.append(f"{p}border_width: 0")
    L.append(f"{p}bg_opa: TRANSP")
    L.append(f"{p}scroll_dir: NONE")
    L.append(f'{p}scrollbar_mode: "OFF"')
    for k, v in props.items():
        L.append(f"{p}{k}: {v}")
    L.append(f"{p}widgets:")


def obj(ident, rect, cor, ind=18, raio=None, **extra):
    x, y, w, h = rect[0], rect[1], rect[2], rect[3]
    r = raio if raio is not None else (rect[4] if len(rect) > 4 else h // 2)
    p = " " * (ind + 4)
    L.append(" " * ind + "- obj:")
    L.append(f"{p}id: {ident}")
    L.append(f"{p}x: {x}")
    L.append(f"{p}y: {y}")
    L.append(f"{p}width: {w}")
    L.append(f"{p}height: {h}")
    L.append(f"{p}radius: {r}")
    L.append(f"{p}border_width: {extra.pop('borda', 0)}")
    if "borda_cor" in extra:
        L.append(f"{p}border_color: {extra.pop('borda_cor')}")
    L.append(f"{p}bg_color: {cor}")
    if "grad" in extra:
        L.append(f"{p}bg_grad_color: {extra.pop('grad')}")
        L.append(f"{p}bg_grad_dir: VER")
    if extra.pop("oculto", False):
        L.append(f"{p}hidden: true")
    for k, v in extra.items():
        L.append(f"{p}{k}: {v}")


def texto(ident, x, y, fonte, cor, txt="", largura=None, alinhar=None,
          longo=None, oculto=False, ind=8):
    p = " " * (ind + 4)
    L.append(" " * ind + "- label:")
    L.append(f"{p}id: {ident}")
    L.append(f"{p}x: {x}")
    L.append(f"{p}y: {y}")
    if largura:
        L.append(f"{p}width: {largura}")
    L.append(f'{p}text: "{txt}"')
    if alinhar:
        L.append(f"{p}text_align: {alinhar}")
    if longo:
        L.append(f"{p}long_mode: {longo}")
    L.append(f"{p}text_font: {fonte}")
    L.append(f"{p}text_color: {cor}")
    if oculto:
        L.append(f"{p}hidden: true")


# ---------------------------------------------------------------- header
L.extend("""# =========================================================================
# ROBOT FACE — geometry from the Jarvis manifest (480x320)
# Structure: page → robo (shake/breathe) → cabeca (tilt) + extras
# (waves, notes, z, dots, rings). Absolute screen coordinates across the
# whole tree; each group is a transparent 480x320 obj at (0,0) with pad 0.
# `obj` only: on this panel LVGL `arc`/`line` came out grey.
# =========================================================================
lvgl:
  buffer_size: 25%
  pages:
    - id: pagina
      x: 0
      y: 0
      width: 100%
      height: 100%
      pad_all: 0
      border_width: 0
      bg_color: 0x05080C
      scroll_dir: NONE
      scrollbar_mode: "OFF"
      widgets:""".splitlines())

# ---------------------------------------------------------------- robot
grupo("robo", 8)

# body
obj("tronco", M["tronco"], "0xE9EFF7", ind=14, grad="0xBCC7D6")
obj("pescoco", M["pescoco"], "0xD6DEEA", ind=14)

# head (group that tilts)
p = " " * 18
L.append(" " * 14 + "- obj:")
for k, v in (("id", "cabeca"), ("x", 0), ("y", 0), ("width", 480), ("height", 320),
             ("pad_all", 0), ("border_width", 0), ("bg_opa", "TRANSP"),
             ("scroll_dir", "NONE"), ("scrollbar_mode", '"OFF"'),
             ("transform_width", "100%"), ("transform_height", "100%"),
# PIVOT AT THE CENTRE: by default LVGL rotates around the top-left corner of the
# object and the head drifted across the screen (seen 29/10).
             ("transform_pivot_x", "50%"), ("transform_pivot_y", "50%")):
    L.append(f"{p}{k}: {v}")
L.append(f"{p}widgets:")

ind = 20
obj("antena", M["antena"], "0xB5C0CE", ind=ind)
obj("led_antena", M["led_antena"], "0xE1FCFF", ind=ind)
obj("orelha_e", M["orelha_e"], "0xCED8E6", ind=ind)
obj("orelha_d", M["orelha_d"], "0xCED8E6", ind=ind)
obj("casca", M["casca"], "0xF6FAFF", ind=ind, grad="0xC6D2E2", borda=1,
    borda_cor="0xFFFFFF")
obj("viseira", M["viseira"], VISEIRA, ind=ind, borda=1, borda_cor="0x263444")
obj("led_orelha_e", M["led_e"], "0x5A6E82", ind=ind)
obj("led_orelha_d", M["led_d"], "0x5A6E82", ind=ind)

# eyes + highlight
for nome, ox in (("e", 179), ("d", 255)):
    obj(f"olho_{nome}", (ox, 159, 46, 54, 50), CIANO, ind=ind)
    obj(f"brilho_{nome}", (ox + 11, 167, 22, 14, 50), "0xF2FEFF", ind=ind)

obj("olho_fechado_e", (179, 183, 46, 9, 4), CIANO, ind=ind, oculto=True)
obj("olho_fechado_d", (255, 183, 46, 9, 4), CIANO, ind=ind, oculto=True)

# eyes as an X (no connection)
for i, cx in enumerate((202, 278)):
    for j, rot in enumerate((45, 135)):
        obj(f"x_{i}_{j}", (cx - 21, 182, 42, 8, 4), VERMELHO, ind=ind,
            oculto=True, transform_rotation=rot)

# eyebrows (crescent)
for nome, r in (("e", M["sobrancelha_e"]), ("d", M["sobrancelha_d"])):
    obj(f"sobrancelha_{nome}", r, CIANO, ind=ind, oculto=True)
    obj(f"sobrancelha_corte_{nome}", (r[0], r[1] + 7, r[2], r[3], r[4]), VISEIRA,
        ind=ind, oculto=True)

# mouths
obj("boca_sorriso", (220, 219, 40, 26, 50), CIANO, ind=ind)
obj("boca_corte", (220, 210, 40, 26, 50), VISEIRA, ind=ind)
obj("boca_aberta", (227, 220, 26, 24, 50), CIANO, ind=ind, oculto=True)
obj("boca_aberta_furo", (234, 227, 12, 11, 50), VISEIRA, ind=ind, oculto=True)
obj("boca_triste", (220, 226, 40, 26, 50), VERMELHO, ind=ind, oculto=True)
obj("boca_triste_corte", (220, 235, 40, 26, 50), VISEIRA, ind=ind, oculto=True)

# -------- extras (outside the head: they do not tilt with it)
obj("onda1", (400, 170, 40, 40, 50), CIANO, ind=14, oculto=True)
obj("onda1_corte", (406, 170, 40, 40, 50), FUNDO, ind=14, oculto=True)
obj("onda2", (386, 156, 68, 68, 50), CIANO, ind=14, oculto=True)
obj("onda2_corte", (392, 156, 68, 68, 50), FUNDO, ind=14, oculto=True)
obj("onda3", (372, 142, 96, 96, 50), CIANO, ind=14, oculto=True)
obj("onda3_corte", (378, 142, 96, 96, 50), FUNDO, ind=14, oculto=True)

for i, (cx, cy, r) in enumerate(((398, 132, 8), (422, 112, 7), (442, 94, 6))):
    obj(f"ponto{i+1}", (cx - r, cy - r, 2 * r, 2 * r, 50), CIANO, ind=14, oculto=True)

for i, r in enumerate((14, 28, 44)):
    obj(f"anel{i+1}", (240 - r, 31 - r, 2 * r, 2 * r, 50), CIANO, ind=14,
        oculto=True, borda=3, borda_cor=CIANO, bg_opa="TRANSP",
        transform_width="100%", transform_height="100%")

# musical notes (each note is a group that rises)
for n, (x, y) in enumerate(((396, 150), (430, 128)), start=1):
    pp = " " * 18
    L.append(" " * 14 + "- obj:")
    L.append(f"{pp}id: nota{n}")
    L.append(f"{pp}x: {x}")
    L.append(f"{pp}y: {y}")
    L.append(f"{pp}width: 22")
    L.append(f"{pp}height: 40")
    L.append(f"{pp}pad_all: 0")
    L.append(f"{pp}border_width: 0")
    L.append(f"{pp}bg_opa: TRANSP")
    L.append(f"{pp}scroll_dir: NONE")
    L.append(f'{pp}scrollbar_mode: "OFF"')
    L.append(f"{pp}hidden: true")
    L.append(f"{pp}widgets:")
    obj(f"nota{n}_cabeca", (0, 28, 12, 10, 50), CIANO, ind=20)
    obj(f"nota{n}_haste", (10, 0, 3, 32, 2), CIANO, ind=20)

# sleep Zs
for i, (x, y, f) in enumerate(((390, 108, "font_normal"), (414, 92, "font_small"),
                               (434, 80, "font_small")), start=1):
    texto(f"z{i}", x, y, f, CIANO, "Z", oculto=True, ind=14)

# alarm exclamation marks
# Alarm exclamation marks drawn by hand (font_med only has digits: "!" came out as
# an empty box). Bar + dot, as in the mockup.
for lado, ex in (("esq", 70), ("dir", 398)):
    obj(f"excl_{lado}_barra", (ex, 120, 6, 26, 3), VERMELHO, ind=8, oculto=True)
    obj(f"excl_{lado}_ponto", (ex, 152, 6, 6, 50), VERMELHO, ind=8, oculto=True)

# ---------------------------------------------------------------- texts
texto("relogio_big", 14, 4, "font_med", "0xFFFFFF", "00:00")
texto("relogio_small", 14, 4, "font_small", TEXTO, "00:00", oculto=True)
texto("temporizador", 396, 12, "font_small", VERMELHO, "", largura=72, alinhar="RIGHT")
# Chest caption, between the shoulders: scrolls in a circle when the text does not fit.
texto("legenda", 150, 298, "font_small", "0x2F3947", "", largura=180,
      alinhar="CENTER", longo="SCROLL_CIRCULAR")

# ---------------------------------------------------------------- animations
L.extend("""  # ---------------------------------------------------------------------
  # Animations. `loop` repeats; the two-halves back-and-forth is done with two
  # animations and `on_stop` starting the opposite one — BUT when that back-and-forth is
  # symmetric there is something better: `timing: round_trip` (ESPHome HAS it), which
  # inside the SAME animation goes from `from` to `to` and back; ending at the
  # initial value, so `loop` produces no jump at all.
  # Only x/y/opa/transform_* are animatable: width and height are NOT.
  # ---------------------------------------------------------------------
  animations:
    # (the mockup breathing is gone: animating the whole-screen group forced
    # LVGL to redraw 480x320 at 60 fps, saturated the SPI at 40 MHz and the voice
    # went slow and glitchy — measured on the panel on 29/10)
    # v0.17.9 — alarm: it used to be a `loop` from -5 to 5 in 90 ms, ~11 jumps per second,
    # faster than the panel draws (it trembled, it did not shake). Now it is a
    # continuous 380 ms back-and-forth with ease_in_out.
    - id: tremer
      duration: 900ms
      loop: true
      timing:
        - type: round_trip
          pause: 0.08
        - type: ease_in_out
      widgets:
        - id: robo
          x:
            from: -4
            to: 4
    - id: inclina_a
      duration: 1200ms
      on_stop:
        # `on_stop` also runs when `lvgl.animation.stop` interrupts it — without
        # this guard, stopping A started B and B started A (endless ping-pong).
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: inclina_b
      widgets:
        - id: cabeca
          transform_rotation:
            from: 0
            to: 5
    - id: inclina_b
      duration: 1200ms
      on_stop:
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: inclina_a
      widgets:
        - id: cabeca
          transform_rotation:
            from: 5
            to: 0
    - id: balanca_a
      duration: 1400ms
      on_stop:
        # `on_stop` also runs when `lvgl.animation.stop` interrupts it — without
        # this guard, stopping A started B and B started A (endless ping-pong).
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: balanca_b
      widgets:
        - id: cabeca
          transform_rotation:
            from: 0
            to: 3
    - id: balanca_b
      duration: 1400ms
      on_stop:
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: balanca_a
      widgets:
        - id: cabeca
          transform_rotation:
            from: 3
            to: 0
    - id: boca_a
      duration: 90ms
      on_stop:
        # `on_stop` also runs when `lvgl.animation.stop` interrupts it — without
        # this guard, stopping A started B and B started A (endless ping-pong).
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: boca_b
      widgets:
        - id: boca_aberta
          y:
            from: 220
            to: 213
    - id: boca_b
      duration: 90ms
      on_stop:
        - if:
            condition:
              lambda: "return id(anim_ok);"
            then:
              - lvgl.animation.start: boca_a
      widgets:
        - id: boca_aberta
          y:
            from: 213
            to: 220
    - id: onda_a
      duration: 700ms
      loop: true
      timing:
        - type: round_trip
      widgets:
        - id: onda1
          opa:
            from: 100%
            to: 25%
        - id: onda2
          opa:
            from: 100%
            to: 25%
        - id: onda3
          opa:
            from: 100%
            to: 25%
    - id: ponto1_anima
      duration: 900ms
      loop: true
      timing:
        - type: round_trip
      widgets:
        - id: ponto1
          opa:
            from: 100%
            to: 30%
    - id: ponto2_anima
      duration: 900ms
      start_delay: 200ms
      loop: true
      timing:
        - type: round_trip
      widgets:
        - id: ponto2
          opa:
            from: 100%
            to: 30%
    - id: ponto3_anima
      duration: 900ms
      start_delay: 400ms
      loop: true
      timing:
        - type: round_trip
      widgets:
        - id: ponto3
          opa:
            from: 100%
            to: 30%
    - id: nota_a
      duration: 2200ms
      loop: true
      widgets:
        - id: nota1
          y:
            from: 150
            to: 88
          opa:
            from: 100%
            to: 10%
    - id: nota_b
      duration: 2200ms
      start_delay: 1100ms
      loop: true
      widgets:
        - id: nota2
          y:
            from: 128
            to: 70
          opa:
            from: 100%
            to: 10%
    - id: z_a
      duration: 2400ms
      loop: true
      widgets:
        - id: z1
          y:
            from: 108
            to: 56
          opa:
            from: 100%
            to: 10%
    - id: z_b
      duration: 2400ms
      start_delay: 800ms
      loop: true
      widgets:
        - id: z2
          y:
            from: 92
            to: 44
          opa:
            from: 100%
            to: 10%
    - id: z_c
      duration: 2400ms
      start_delay: 1600ms
      loop: true
      widgets:
        - id: z3
          y:
            from: 80
            to: 36
          opa:
            from: 100%
            to: 10%
    - id: anel_1
      duration: 900ms
      loop: true
      widgets:
        - id: anel1
          transform_width:
            from: 40%
            to: 100%
          transform_height:
            from: 40%
            to: 100%
          opa:
            from: 100%
            to: 0%
    - id: anel_2
      duration: 900ms
      start_delay: 300ms
      loop: true
      widgets:
        - id: anel2
          transform_width:
            from: 40%
            to: 100%
          transform_height:
            from: 40%
            to: 100%
          opa:
            from: 100%
            to: 0%
    - id: anel_3
      duration: 900ms
      start_delay: 600ms
      loop: true
      widgets:
        - id: anel3
          transform_width:
            from: 40%
            to: 100%
          transform_height:
            from: 40%
            to: 100%
          opa:
            from: 100%
            to: 0%
    - id: olhos_saltam
      duration: 600ms
      loop: true
      timing:
        - type: round_trip
          pause: 0.05
      widgets:
        - id: olho_e
          x:
            from: 179
            to: 185
        - id: olho_d
          x:
            from: 255
            to: 261
    - id: led_pulsa
      duration: 700ms
      loop: true
      timing:
        - type: round_trip
      widgets:
        - id: led_antena
          opa:
            from: 100%
            to: 25%""".splitlines())

# v0.17.13 — writes next to the generator (it lives in ~/homelab/esphome-build/geradores)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bloco_lvgl.yaml"),
     "w", encoding="utf-8").write(
    "\n".join(L) + "\n")
print("bloco lvgl gerado:", len(L), "linhas")
