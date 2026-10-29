"""Geometria unica da cara do robo (480x320) — fonte para o preview e para o YAML LVGL.

Tudo medido nos mockups do Jarvis (Espelho: Agentes/Jarvis/mockups-cara-2026-10-29),
a 29/10/2026, com mede_mockup.py (componentes conexas por cor).
"""

W, H = 480, 320

# Cores (medidas nos PNG)
PRETO = (0x00, 0x00, 0x00)
FUNDO = (0x00, 0x00, 0x00)
CORPO = (0xE7, 0xEC, 0xF2)         # branco azulado do corpo (topo do gradiente)
CORPO_BAIXO = (0xC6, 0xCF, 0xDB)   # base do gradiente
ECRA = (0x09, 0x0E, 0x15)          # preto do ecra interior
ORELHA = (0xCE, 0xD8, 0xE6)
ANTENA = (0x99, 0xAF, 0xBE)
PONTA = (0xE1, 0xFC, 0xFF)
CIANO = (0x40, 0xE0, 0xFF)
BRANCO = (0xFF, 0xFF, 0xFF)
VERMELHO = (0xFF, 0x4D, 0x4D)
CINZA_TEXTO = (0x96, 0xA8, 0xBE)

# Elementos fixos (x, y, w, h, raio)
CORPO_RECT = (122, 77, 237, 207, 77)
ECRA_RECT = (150, 122, 181, 131, 57)
ORELHA_ESQ = (104, 178, 16, 47, 8)
ORELHA_DIR = (361, 178, 16, 47, 8)
ANTENA_RECT = (238, 40, 5, 37, 2)
PONTA_RECT = (231, 22, 19, 19, 9)

# Olhos/almofadas por estado: (esq, dir) cada um (x, y, w, h, raio)
OLHOS = {
    "espera":  ((179, 159, 47, 55, 22), (254, 159, 47, 55, 22)),
    "ouvir":   ((174, 158, 57, 57, 28), (250, 158, 57, 57, 28)),
    "pensar":  ((182, 154, 47, 52, 22), (258, 147, 47, 52, 22)),
    "falar":   ((179, 159, 47, 55, 22), (254, 159, 47, 55, 22)),
    "musica":  ((183, 158, 42, 20, 10), (258, 164, 43, 21, 10)),
    "alarme":  ((174, 154, 57, 57, 28), (250, 154, 57, 57, 28)),
}

# Boca: ("tipo", x, y, w, h) — tipo em arco_sorriso | arco_triste | linha | circulo
BOCAS = {
    "espera": ("arco_sorriso", (213, 194, 55, 55)),
    "ouvir":  ("linha", (224, 230, 33, 5)),
    "pensar": ("linha", (230, 229, 33, 7)),
    "falar":  ("circulo", (230, 220, 24, 20)),
    "musica": ("arco_sorriso", (213, 194, 55, 55)),
    "noite":  ("arco_sorriso", (213, 194, 55, 55)),
    "erro":   ("arco_triste", (215, 226, 49, 49)),
    "alarme": ("circulo", (230, 226, 26, 26)),
}

# Reflexo branco dentro de cada olho (x, y, w, h) — so nos estados com olho redondo
REFLEXO = {"espera": (7, 6, 33, 21), "ouvir": (11, 8, 33, 21),
           "falar": (7, 6, 33, 21), "alarme": (11, 8, 33, 21)}

# Sobrancelhas (so "ouvir")
SOBRANCELHAS = ((184, 141, 37, 9), (259, 141, 37, 9))

# Ondas sonoras ("ouvir"): 3 arcos a direita da cabeca
ONDAS = [(440, 190, 12), (440, 190, 22), (440, 190, 32)]
PENSAMENTO = [(390, 124, 17), (415, 105, 15), (436, 88, 13)]  # circulos

# Texto
REL_BIG = (16, 8, 40)      # relogio em espera: canto sup. esq., fonte 40
REL_SMALL = (15, 13, 16)   # relogio nos outros estados
LEGENDA_Y = 293            # topo da legenda (fonte 16) — abaixo do corpo (acaba em 284)
TEMP_POS = (404, 10)       # temporizador: canto sup. direito, vermelho, fonte 16

# Estado -> legenda
LEGENDAS = {
    "espera": "",
    "ouvir": "A OUVIR...",
    "pensar": "A PENSAR...",
    "falar": "A FALAR",
    "musica": "A TOCAR",
    "noite": "A DORMIR",
    "erro": "SEM LIGAÇÃO",
    "alarme": "ALARME",
}
