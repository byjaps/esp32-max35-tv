"""Mede quanto tempo o painel fica no estado 'a tocar' (ec=4) depois de o som acabar."""
import asyncio
import json
import re
import sys
import time
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

from aioesphomeapi import APIClient  # noqa: E402

CHAVE = re.search(r'api_encryption_key:\s*"([^"]+)"',
                  open("/home/hermes/homelab/esphome-build/secrets.yaml").read()).group(1)


def post(s, d):
    rq = urllib.request.Request(f"{BASE}/api/services/{s}", data=json.dumps(d).encode(),
                                headers=HEADERS, method="POST")
    return urllib.request.urlopen(rq, timeout=30).status


async def main():
    post("timer/start", {"entity_id": "timer.temporizador_2", "duration": 120})
    await asyncio.sleep(1)
    cli = APIClient("192.168.31.135", 6053, None, noise_psk=CHAVE)
    await cli.connect(login=True)
    ents, _ = await cli.list_entities_services()
    k = next(e.key for e in ents if getattr(e, "name", "") == "Depuracao contagem")
    ultimo = []

    def cb(s):
        if s.key == k:
            ultimo.append((time.time(), getattr(s, "state", "")))

    cli.subscribe_states(cb)
    await asyncio.sleep(1)
    t0 = time.time()
    post("media_player/play_media", {"entity_id": "media_player.mini_tv_painel_de_voz",
                                     "media_content_id": "http://192.168.31.180:8123/local/sons/alarme_atual.wav",
                                     "media_content_type": "music"})
    await asyncio.sleep(30)
    await cli.disconnect()
    post("timer/cancel", {"entity_id": "timer.temporizador_2"})
    for ts, linha in ultimo:
        m = dict(p.split("=") for p in linha.split() if "=" in p)
        print(f"{ts-t0:5.1f}s mp={m.get('mp')} ec={m.get('ec')}")


asyncio.run(main())
