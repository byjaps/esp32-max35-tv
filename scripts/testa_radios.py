"""Testa a mudança de estação: manda tocar duas rádios no painel pelo Music
Assistant e vê se o título escrito no painel acompanha."""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

PAINEL_MA = "media_player.mini_tv_painel_de_voz_2"

RADIOS = [
    ("RFM", "https://24223.live.streamtheworld.com/RFM_SC"),
    ("Antena 1", "https://radiocast.rtp.pt/antena180a.mp3"),
]


def post(s, d):
    rq = urllib.request.Request(f"{BASE}/api/services/{s}", data=json.dumps(d).encode(),
                                headers=HEADERS, method="POST")
    return urllib.request.urlopen(rq, timeout=60).status


def ver(rotulo):
    linhas = []
    for e in (PAINEL_MA, "media_player.mini_tv_painel_de_voz", "text.mini_tv_titulo_do_media"):
        s = json.load(urllib.request.urlopen(
            urllib.request.Request(f"{BASE}/api/states/{e}", headers=HEADERS), timeout=20))
        extra = s["attributes"].get("media_title") or s["state"]
        linhas.append(f"{e.split('.')[-1]}={extra!r}")
    print(f"{rotulo}: " + " | ".join(linhas))


for nome, url in RADIOS:
    try:
        post("media_player/play_media", {"entity_id": PAINEL_MA,
                                         "media_content_id": url,
                                         "media_content_type": "music"})
    except Exception as e:  # noqa: BLE001
        print(nome, "erro:", e)
    time.sleep(8)
    ver(nome)

post("media_player/media_stop", {"entity_id": PAINEL_MA})
