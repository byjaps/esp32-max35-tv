"""Gera a secção `lvgl:` da cara do robô a partir do manifest do Jarvis (v1.0).

Porquê um gerador: são ~90 widgets com coordenadas medidas no manifest; assim as
coordenadas ficam num sítio só e o YAML sai sempre igual.

Duas lições do painel (29/10), que é o que justifica este ficheiro existir:
  * `arc` e `line` do LVGL saíram CINZENTOS no dispositivo e no alarme desenhavam
    uma caixa à frente da cara → tudo é `obj`, cujo `bg_color` pinta sempre;
  * crescentes (boca, sobrancelhas, ondas) = elipse cheia + elipse da cor do fundo
    deslocada por cima.
"""
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
    "olho_e": (179, 159, 46, 54, 50),
    "olho_d": (255, 159, 46, 54, 50),
    "sobrancelha_e": (183, 141, 38, 18, 50),
    "sobrancelha_d": (259, 141, 38, 18, 50),
}

FUNDO = "0x05080C"
VISEIRA = "0x090E15"
CIANO = "0x40E0FF"
VERMELHO = "0xFF6060"
TEXTO = "0x96A8BE"

linhas = []


def obj(ident, rect, cor, ind=14, raio=None, **extra):
    """Um `obj`; `ind` é a indentação do '-' (14 = dentro do grupo robo)."""
    x, y, w, h = rect[0], rect[1], rect[2], rect[3]
    r = raio if raio is not None else (rect[4] if len(rect) > 4 else h // 2)
    p = " " * (ind + 4)
    linhas.append(" " * ind + "- obj:")
    linhas.append(f"{p}id: {ident}")
    linhas.append(f"{p}x: {x}")
    linhas.append(f"{p}y: {y}")
    linhas.append(f"{p}width: {w}")
    linhas.append(f"{p}height: {h}")
    linhas.append(f"{p}radius: {r}")
    linhas.append(f"{p}border_width: {extra.pop('borda', 0)}")
    if "borda_cor" in extra:
        linhas.append(f"{p}border_color: {extra.pop('borda_cor')}")
    linhas.append(f"{p}bg_color: {cor}")
    if "grad" in extra:
        linhas.append(f"{p}bg_grad_color: {extra.pop('grad')}")
        linhas.append(f"{p}bg_grad_dir: VER")
    if extra.pop("oculto", False):
        linhas.append(f"{p}hidden: true")
    for k, v in extra.items():
        linhas.append(f"{p}{k}: {v}")


def label(ident, x, y, fonte, cor, texto="", largura=None, alinhar=None, oculto=False):
    p = " " * 12
    linhas.append("        - label:")
    linhas.append(f"{p}id: {ident}")
    linhas.append(f"{p}x: {x}")
    linhas.append(f"{p}y: {y}")
    if largura:
        linhas.append(f"{p}width: {largura}")
    linhas.append(f'{p}text: "{texto}"')
    if alinhar:
        linhas.append(f"{p}text_align: {alinhar}")
    linhas.append(f"{p}text_font: {fonte}")
    linhas.append(f"{p}text_color: {cor}")
    if oculto:
        linhas.append(f"{p}hidden: true")


# ---------------------------------------------------------------- cabeçalho
linhas.extend("""# =========================================================================
# CARA DO ROBÔ — geometria do manifest do Jarvis (480x320)
# Só `obj`: no painel os `arc` e `line` do LVGL saíam CINZENTOS (a cor do tema
# ganha) e no alarme desenhavam uma caixa à frente da cara. `bg_color` pinta
# sempre. Crescentes = elipse cheia + elipse da cor do fundo por cima.
# `robo` agrupa o que treme/respira: mexer o x/y do grupo move o conjunto.
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
      widgets:""".splitlines())

# ---------------------------------------------------------------- grupo robo
linhas.extend("""        - obj:
            id: robo
            x: 0
            y: 0
            width: 480
            height: 320
            pad_all: 0
            border_width: 0
            bg_opa: TRANSP
            widgets:""".splitlines())

# --- corpo (por trás da cabeça)
obj("pescoco", M["pescoco"], "0xD6DEEA")
obj("tronco", M["tronco"], "0xE9EFF7", grad="0xBCC7D6")

# --- antena e LED
obj("antena", M["antena"], "0xB5C0CE")
obj("led_antena", M["led_antena"], "0xE1FCFF")

# --- cabeça
obj("orelha_e", M["orelha_e"], "0xCED8E6")
obj("orelha_d", M["orelha_d"], "0xCED8E6")
obj("casca", M["casca"], "0xF6FAFF", grad="0xC6D2E2", borda=1, borda_cor="0xFFFFFF")
obj("viseira", M["viseira"], VISEIRA, borda=1, borda_cor="0x263444")
obj("led_orelha_e", M["led_e"], "0x5A6E82")
obj("led_orelha_d", M["led_d"], "0x5A6E82")

# --- olhos abertos + brilho
for nome, ox, oy in (("e", 179, 159), ("d", 255, 159)):
    obj(f"olho_{nome}", (ox, oy, 46, 54, 50), CIANO)
    obj(f"brilho_{nome}", (ox + 11, oy + 8, 22, 14, 50), "0xF2FEFF")

# --- olhos fechados (barras)
obj("olho_fechado_e", (179, 183, 46, 9, 4), CIANO, oculto=True)
obj("olho_fechado_d", (255, 183, 46, 9, 4), CIANO, oculto=True)

# --- olhos em X (sem ligação): 2 barras diagonais por olho
for i, cx in enumerate((202, 278)):
    for j, rot in enumerate((45, 135)):
        obj(f"x_{i}_{j}", (cx - 21, 182, 42, 8, 4), VERMELHO,
            oculto=True, transform_rotation=rot)

# --- sobrancelhas (crescente virado para cima)
for nome, r in (("e", M["sobrancelha_e"]), ("d", M["sobrancelha_d"])):
    obj(f"sobrancelha_{nome}", r, CIANO, oculto=True)
    obj(f"sobrancelha_corte_{nome}", (r[0], r[1] + 7, r[2], r[3], r[4]), VISEIRA, oculto=True)

# --- boca: sorriso (crescente para baixo, centro 240,232)
obj("boca_sorriso", (220, 219, 40, 26, 50), CIANO)
obj("boca_corte", (220, 210, 40, 26, 50), VISEIRA)

# --- boca aberta (a falar / alarme)
obj("boca_aberta", (227, 220, 26, 24, 50), CIANO, oculto=True)
obj("boca_aberta_furo", (234, 227, 12, 11, 50), VISEIRA, oculto=True)

# --- boca triste (sem ligação)
obj("boca_triste", (220, 226, 40, 26, 50), VERMELHO, oculto=True)
obj("boca_triste_corte", (220, 235, 40, 26, 50), VISEIRA, oculto=True)

# --- ondas (a ouvir): centro 420,190; crescentes virados ao robô
for i, r in enumerate((20, 34, 48)):
    obj(f"onda{i+1}", (420 - r, 190 - r, 2 * r, 2 * r, 50), CIANO, oculto=True)
    obj(f"onda{i+1}_corte", (420 - r + 6, 190 - r, 2 * r, 2 * r, 50), FUNDO, oculto=True)

# --- pontos de pensamento
for i, (cx, cy, r) in enumerate(((398, 132, 8), (422, 112, 7), (442, 94, 6))):
    obj(f"ponto{i+1}", (cx - r, cy - r, 2 * r, 2 * r, 50), CIANO, oculto=True)

# --- anéis do alarme a sair do LED da antena (centro 240,31)
for i, r in enumerate((14, 28, 44)):
    obj(f"anel{i+1}", (240 - r, 31 - r, 2 * r, 2 * r, 50), CIANO,
        oculto=True, borda=3, borda_cor=CIANO, bg_opa="TRANSP")

# --- exclamações do alarme
linhas.extend("""        - label:
            id: exclamacao_esq
            x: 66
            y: 132
            text: "!"
            text_font: font_med
            text_color: 0xFF6060
            hidden: true
        - label:
            id: exclamacao_dir
            x: 354
            y: 132
            text: "!"
            text_font: font_med
            text_color: 0xFF6060
            hidden: true""".splitlines())

# ---------------------------------------------------------------- textos
label("relogio_big", 14, 4, "font_med", "0xFFFFFF", "00:00")
label("relogio_small", 14, 4, "font_small", TEXTO, "00:00", oculto=True)
label("legenda", 0, 297, "font_small", "0x2F3947", "", largura=480, alinhar="CENTER")
label("temporizador", 396, 12, "font_small", VERMELHO, "", largura=72, alinhar="RIGHT")

# ---------------------------------------------------------------- animações
linhas.extend("""  # Animações: respirar (espera), tremer (alarme), pulsar (ondas e anéis),
  # boca a falar. Só se mexe em `x`/`y`/`opa` — as que o LVGL aceita animar.
  # Vão debaixo de `animations:` (uma lista), não como itens soltos do lvgl.
  animations:
    - id: respirar
      duration: 3s
      loop: true
      widgets:
        - id: robo
          y:
            from: 0
            to: 2
    - id: tremer
      duration: 90ms
      loop: true
      widgets:
        - id: robo
          x:
            from: -5
            to: 5
    - id: pulsar_ondas
      duration: 700ms
      loop: true
      widgets:
        - id: onda1
          opa:
            from: 100%
            to: 20%
        - id: onda2
          opa:
            from: 100%
            to: 20%
        - id: onda3
          opa:
            from: 100%
            to: 20%
    - id: pulsar_anel
      duration: 640ms
      loop: true
      widgets:
        - id: anel1
          opa:
            from: 100%
            to: 10%
        - id: anel2
          opa:
            from: 100%
            to: 10%
        - id: anel3
          opa:
            from: 100%
            to: 10%
    - id: falar_boca
      duration: 180ms
      loop: true
      widgets:
        - id: boca_aberta
          y:
            from: 220
            to: 213""".splitlines())

open("/home/hermes/.hermes/cache/scratch/bloco_lvgl.yaml", "w", encoding="utf-8").write(
    "\n".join(linhas) + "\n")
print("bloco lvgl gerado:", len(linhas), "linhas")
