"""Desenha a cara com as MESMAS coordenadas do gerador (../geradores/gera_face.py) em PIL.

Serve de prova visual antes de cada OTA: se o preview estiver certo e o painel não,
o problema é do LVGL (cor/empilhamento), não da geometria.

Uso: python3 preview_lvgl.py [pasta_saida]
Gera <estado>.png (480x320) + folha.png com os 8 estados.
"""
import importlib.util
import os
import sys
from PIL import Image, ImageDraw

GERADOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "geradores", "gera_face.py")
spec = importlib.util.spec_from_file_location("gf", GERADOR)
gf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gf)          # escreve o bloco lvgl (efeito colateral inofensivo)
M = gf.M
SAIDA = sys.argv[1] if len(sys.argv) > 1 else "preview"
os.makedirs(SAIDA, exist_ok=True)

W, H = 480, 320
FUNDO = (5, 8, 12)
VISEIRA = (9, 14, 21)
CIANO = (64, 224, 255)
VERM = (255, 96, 96)
TXT = (150, 168, 190)


def esc(h):
    h = h.lstrip("0x")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


CASCA1, CASCA2 = esc("F6FAFF"), esc("C6D2E2")
TRONCO1, TRONCO2 = esc("E9EFF7"), esc("BCC7D6")


def rr(d, r, cor, raio=None):
    x, y, w, h = r[:4]
    rad = raio if raio is not None else (r[4] if len(r) > 4 else h // 2)
    if rad >= 50:      # 50 = circulo/elipse em percentagem
        d.ellipse([x, y, x + w - 1, y + h - 1], fill=cor)
    else:
        d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=rad, fill=cor)


def grad(d, r, c1, c2, raio):
    x, y, w, h = r[:4]
    faixa = Image.new("RGB", (1, h))
    fd = ImageDraw.Draw(faixa)
    for i in range(h):
        f = i / max(h - 1, 1)
        fd.point((0, i), fill=tuple(int(c1[k] * (1 - f) + c2[k] * f) for k in range(3)))
    faixa = faixa.resize((w, h))
    masc = Image.new("L", (w, h), 0)
    ImageDraw.Draw(masc).rounded_rectangle([0, 0, w - 1, h - 1], radius=raio, fill=255)
    return faixa, masc


def frame(estado):
    im = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(im)

    # corpo
    rr(d, M["pescoco"], esc("D6DEEA"))
    faixa, masc = grad(d, M["tronco"], TRONCO1, TRONCO2, M["tronco"][4])
    im.paste(faixa, (M["tronco"][0], M["tronco"][1]), masc)
    rr(d, M["antena"], esc("B5C0CE"))
    rr(d, M["led_antena"], esc("E1FCFF"))
    rr(d, M["orelha_e"], esc("CED8E6"))
    rr(d, M["orelha_d"], esc("CED8E6"))
    faixa, masc = grad(d, M["casca"], CASCA1, CASCA2, M["casca"][4])
    im.paste(faixa, (M["casca"][0], M["casca"][1]), masc)
    rr(d, M["viseira"], VISEIRA)
    rr(d, M["led_e"], esc("5A6E82"))
    rr(d, M["led_d"], esc("5A6E82"))

    olhos_fechados = estado in ("musica", "noite")
    erro = estado == "erro"
    alarme = estado == "alarme"

    if erro:
        for cx in (202, 278):
            for a in (-1, 1):
                d.line([cx - 15, 186 - 15 * a, cx + 15, 186 + 15 * a], fill=VERM, width=8)
    elif olhos_fechados:
        rr(d, (179, 183, 46, 9, 4), CIANO)
        rr(d, (255, 183, 46, 9, 4), CIANO)
    else:
        for ox in (179, 255):
            rr(d, (ox, 159, 46, 54, 50), CIANO)
            rr(d, (ox + 11, 167, 22, 14, 50), (242, 254, 255))

    # sobrancelhas (a ouvir)
    if estado == "ouvir":
        for sx in (183, 259):
            rr(d, (sx, 141, 38, 18, 50), CIANO)
            rr(d, (sx, 148, 38, 18, 50), VISEIRA)

    # boca
    if alarme or estado == "falar":
        rr(d, (227, 220, 26, 24, 50), CIANO)
        rr(d, (234, 227, 12, 11, 50), VISEIRA)
    elif erro:
        rr(d, (220, 226, 40, 26, 50), VERM)
        rr(d, (220, 235, 40, 26, 50), VISEIRA)
    else:
        rr(d, (220, 219, 40, 26, 50), CIANO)
        rr(d, (220, 210, 40, 26, 50), VISEIRA)

    # ondas
    if estado == "ouvir" or alarme:
        for r in (20, 34, 48):
            rr(d, (420 - r, 190 - r, 2 * r, 2 * r, 50), CIANO)
            rr(d, (420 - r + 6, 190 - r, 2 * r, 2 * r, 50), FUNDO)

    if estado == "pensar":
        for cx, cy, r in ((398, 132, 8), (422, 112, 7), (442, 94, 6)):
            rr(d, (cx - r, cy - r, 2 * r, 2 * r, 50), CIANO)

    if alarme:
        for r in (14, 28, 44):
            d.ellipse([240 - r, 31 - r, 240 + r, 31 + r], outline=CIANO, width=3)
        rr(d, M["led_antena"], VERM)

    return im


def com_texto(im, legenda, relogio_grande):
    d = ImageDraw.Draw(im)
    if relogio_grande:
        d.text((16, 14), "22:10", fill=(255, 255, 255))
    else:
        d.text((16, 16), "22:10", fill=TXT)
    if legenda:
        w = d.textlength(legenda)
        d.text(((W - w) / 2, 297), legenda, fill=(47, 57, 71))
    return im


ESTADOS = [("espera", "ESPERA", True), ("ouvir", "A OUVIR", False), ("pensar", "A PENSAR", False),
           ("falar", "A FALAR", False), ("musica", "A TOCAR", False), ("noite", "A DORMIR", False),
           ("erro", "SEM LIGAÇÃO", False), ("alarme", "ALARME", False)]

folha = Image.new("RGB", (W * 2, H * 4), (30, 30, 30))
for i, (est, leg, grande) in enumerate(ESTADOS):
    im = com_texto(frame(est), leg, grande)
    im.save(f"{SAIDA}/{est}.png")
    folha.paste(im, ((i % 2) * W, (i // 2) * H))
folha.save(f"{SAIDA}/folha.png")
print("preview escrito em", SAIDA)
