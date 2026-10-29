"""Testa as duas vias do título do painel:
  1. via Music Assistant (metadados reais);
  2. via play_media directo do HA (nome derivado do URL) — não pode ficar com o
     nome da coisa anterior.
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

PAINEL = "media_player.mini_tv_painel_de_voz"
MA = "media_player.mini_tv_painel_de_voz_2"


def post(s, d):
    rq = urllib.request.Request(f"{BASE}/api/services/{s}", data=json.dumps(d).encode(),
                                headers=HEADERS, method="POST")
    return urllib.request.urlopen(rq, timeout=60).status


def titulo():
    s = json.load(urllib.request.urlopen(
        urllib.request.Request(f"{BASE}/api/states/text.mini_tv_titulo_do_media",
                               headers=HEADERS), timeout=20))
    return s["state"]


# 1) Music Assistant
post("media_player/play_media", {"entity_id": MA,
                                 "media_content_id": "https://radiocast.rtp.pt/antena180a.mp3",
                                 "media_content_type": "music"})
time.sleep(10)
print("MA (Antena 1):", repr(titulo()))

# pára e confirma que limpa
post("media_player/media_stop", {"entity_id": MA})
time.sleep(6)
print("depois de parar:", repr(titulo()))

# 2) play_media directo ao painel (via HA)
post("media_player/play_media", {"entity_id": PAINEL,
                                 "media_content_id": "https://24223.live.streamtheworld.com/RFM_SC",
                                 "media_content_type": "music"})
time.sleep(10)
print("HA directo (URL da RFM):", repr(titulo()))

post("media_player/media_stop", {"entity_id": PAINEL})
time.sleep(6)
print("depois de parar (HA):", repr(titulo()))
