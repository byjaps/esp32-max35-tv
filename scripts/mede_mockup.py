"""Mede a geometria dos mockups da cara do robo (480x320) com componentes conexas."""
from PIL import Image
import numpy as np
import sys, json

D = "/home/hermes/obsidian/Homelab/Agentes/Jarvis/mockups-cara-2026-10-29/"


def blobs(mask, min_area=80):
    """Componentes conexas (4-vizinhos) por BFS iterativo. Devolve lista de dicts."""
    m = mask.copy()
    h, w = m.shape
    saida = []
    for y in range(h):
        linha = m[y]
        for x in np.nonzero(linha)[0]:
            if not m[y, x]:
                continue
            pilha = [(y, x)]
            m[y, x] = False
            ys, xs = [], []
            while pilha:
                cy, cx = pilha.pop()
                ys.append(cy); xs.append(cx)
                for ny, nx in ((cy-1, cx), (cy+1, cx), (cy, cx-1), (cy, cx+1)):
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx]:
                        m[ny, nx] = False
                        pilha.append((ny, nx))
            if len(ys) >= min_area:
                ys = np.array(ys); xs = np.array(xs)
                saida.append(dict(x=int(xs.min()), y=int(ys.min()),
                                  w=int(xs.max()-xs.min()+1), h=int(ys.max()-ys.min()+1),
                                  area=int(len(ys)),
                                  cx=int(xs.mean()), cy=int(ys.mean())))
    saida.sort(key=lambda b: -b["area"])
    return saida


def cores(img):
    a = np.array(img.convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return a, {
        "branco": (R > 200) & (G > 200) & (B > 200),
        "ciano": (G > 170) & (B > 190) & (R < 150),
        "vermelho": (R > 170) & (G < 90) & (B < 90),
        "cinza": (abs(R-G) < 14) & (abs(G-B) < 14) & (R > 60) & (R < 200),
        "preto": (R < 40) & (G < 40) & (B < 40),
    }


if __name__ == "__main__":
    ficheiro = sys.argv[1] if len(sys.argv) > 1 else "01-idle.png"
    img = Image.open(D + ficheiro)
    a, ms = cores(img)
    print("==", ficheiro, img.size)
    for nome in ("branco", "preto", "ciano", "vermelho", "cinza"):
        bs = blobs(ms[nome], 120)
        print(f"-- {nome}: {len(bs)} blobs")
        for b in bs[:6]:
            print("   ", b)
