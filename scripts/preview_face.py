"""Desenha a cara do robo com a MESMA geometria que vai para o LVGL (preview antes do OTA).

Uso: python3 preview_face.py [pasta_saida]
Gera <estado>.png (480x320) para cada estado + folha.png com todos lado a lado.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import face_spec as G

FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not os.path.exists(FONTE):
    FONTE = ImageFont.truetype  # noqa


def fonte(px):
    try:
        return ImageFont.truetype(FONTE, px)
    except Exception:
        return ImageFont.load_default()


def rr(d, rect, cor, raio):
    x, y, w, h = rect[:4]
    r = raio
    d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=r, fill=cor)


def desenha(estado, relogio="21:27", legenda_extra=None, temporizador=None):
    im = Image.new("RGB", (G.W, G.H), G.FUNDO)
    d = ImageDraw.Draw(im)
    dim = estado == "noite"

    corpo = tuple(int(c * 0.45) for c in G.CORPO) if dim else G.CORPO
    orelha = tuple(int(c * 0.45) for c in G.ORELHA) if dim else G.ORELHA
    ciano = tuple(int(c * 0.5) for c in G.CIANO) if dim else G.CIANO
    verm = G.VERMELHO

    # antena (por tras do corpo)
    rr(d, G.ANTENA_RECT, G.ANTENA if not dim else (60, 66, 76), G.ANTENA_RECT[4])
    d.ellipse([G.PONTA_RECT[0], G.PONTA_RECT[1],
               G.PONTA_RECT[0] + G.PONTA_RECT[2], G.PONTA_RECT[1] + G.PONTA_RECT[3]],
              fill=G.PONTA if not dim else (70, 78, 90))
    # orelhas
    rr(d, G.ORELHA_ESQ, orelha, G.ORELHA_ESQ[4])
    rr(d, G.ORELHA_DIR, orelha, G.ORELHA_DIR[4])
    # corpo com gradiente vertical (como no mockup) + ecra
    cx, cy, cw, ch, craio = G.CORPO_RECT
    grad = Image.new("RGB", (1, ch))
    gd = ImageDraw.Draw(grad)
    for i in range(ch):
        f = i / max(ch - 1, 1)
        gd.point((0, i), fill=tuple(int(G.CORPO[k] * (1 - f) + G.CORPO_BAIXO[k] * f) for k in range(3)))
    grad = grad.resize((cw, ch))
    mascara = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=craio, fill=255)
    im.paste(grad, (cx, cy), mascara)
    rr(d, G.ECRA_RECT, G.ECRA, G.ECRA_RECT[4])

    # olhos
    if estado in G.OLHOS:
        esq, dir_ = G.OLHOS[estado]
        rr(d, esq, ciano, esq[4])
        rr(d, dir_, ciano, dir_[4])
        if estado in G.REFLEXO:
            rx, ry, rw, rh = G.REFLEXO[estado]
            for olho in (esq, dir_):
                d.ellipse([olho[0] + rx, olho[1] + ry,
                           olho[0] + rx + rw, olho[1] + ry + rh], fill=G.BRANCO)
    elif estado == "erro":
        for (cx, cy) in ((202, 190), (278, 190)):
            for s in (1, -1):
                d.line([cx - 14 * s, cy - 14, cx + 14 * s, cy + 14], fill=verm, width=7)
                d.line([cx - 14 * s, cy + 14, cx + 14 * s, cy - 14], fill=verm, width=7)
    elif estado == "noite":
        for (x0, y0) in ((183, 190), (258, 190)):
            d.line([x0, y0, x0 + 42, y0], fill=ciano, width=6)

    # boca
    tipo, (mx, my, mw, mh) = G.BOCAS.get(estado, G.BOCAS["espera"])
    cor_boca = verm if estado == "erro" else ciano
    if tipo == "circulo":
        d.ellipse([mx, my, mx + mw, my + mh], fill=cor_boca)
    elif tipo == "arco_triste":
        d.arc([mx, my, mx + mw, my + mh], start=220, end=320, fill=cor_boca, width=5)
    elif tipo == "arco_sorriso":
        d.arc([mx, my, mx + mw, my + mh], start=39, end=141, fill=cor_boca, width=6)
    else:
        rr(d, (mx, my, mw, mh), cor_boca, min(mw, mh) // 2)

    # extras de estado
    if estado in ("ouvir", "alarme"):
        for (cx, cy, r) in G.ONDAS:
            d.arc([cx - r, cy - r, cx + r, cy + r], start=-55, end=55,
                  fill=ciano, width=4)
        if estado == "ouvir":
            for sb in G.SOBRANCELHAS:
                rr(d, sb, ciano, 4)
    if estado == "pensar":
        for (cx, cy, r) in G.PENSAMENTO:
            d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], fill=ciano)
    if estado == "musica":
        f = fonte(34)
        d.text((392, 100), "\u266a", font=f, fill=ciano)
        d.text((428, 78), "\u266b", font=f, fill=ciano)
    if estado == "noite":
        d.text((300, 205), "z z z", font=fonte(22), fill=G.CINZA_TEXTO)

    # relogio
    if estado == "espera":
        x, y, sz = G.REL_BIG
        d.text((x, y), relogio, font=fonte(sz), fill=G.BRANCO)
    else:
        x, y, sz = G.REL_SMALL
        d.text((x, y), relogio, font=fonte(sz), fill=G.BRANCO)

    # legenda
    texto = legenda_extra if legenda_extra is not None else G.LEGENDAS.get(estado, "")
    if texto:
        f = fonte(16)
        cor = verm if estado in ("erro", "alarme") else G.BRANCO
        larg = d.textlength(texto, font=f)
        d.text(((G.W - larg) / 2, G.LEGENDA_Y), texto, font=f, fill=cor)

    # temporizador (canto superior direito, vermelho, 16 px)
    if temporizador:
        f = fonte(16)
        larg = d.textlength(temporizador, font=f)
        d.text((G.TEMP_POS[0] + 60 - larg, G.TEMP_POS[1]), temporizador, font=f, fill=verm)
    return im


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.hermes/cache/scratch/preview")
    os.makedirs(saida, exist_ok=True)
    estados = ["espera", "ouvir", "pensar", "falar", "musica", "noite", "erro", "alarme"]
    ims = []
    for e in estados:
        temporizador = "12:34" if e in ("espera", "falar") else None
        im = desenha(e, legenda_extra="A TOCAR · ANTENA 3" if e == "musica" else None,
                     temporizador=temporizador)
        im.save(os.path.join(saida, f"{e}.png"))
        ims.append((e, im))
    folha = Image.new("RGB", (G.W * 2 + 12, (G.H + 12) * 4 + 12), (30, 30, 30))
    for i, (e, im) in enumerate(ims):
        folha.paste(im, ((i % 2) * (G.W + 12) + 4, (i // 2) * (G.H + 12) + 4))
    folha.save(os.path.join(saida, "folha.png"))
    print("escrito em", saida)
