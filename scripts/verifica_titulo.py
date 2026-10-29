"""Verifica: (1) nome do que toca chega ao text entity do painel; (2) o ecra volta
a espera quando o media acaba."""
import asyncio
import json
import re
import sys
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

from aioesphomeapi import APIClient  # noqa: E402

CHAVE = re.search(r'api_encryption_key:\s*"([^"]+)"',
                  open("/home/hermes/homelab/esphome-build/secrets.yaml").read()).group(1)


def post(servico, dados):
    rq = urllib.request.Request(f"{BASE}/api/services/{servico}",
                                data=json.dumps(dados).encode(),
                                headers=HEADERS, method="POST")
    return urllib.request.urlopen(rq, timeout=30).status


def st(entidade, attr=None):
    s = json.load(urllib.request.urlopen(
        urllib.request.Request(f"{BASE}/api/states/{entidade}", headers=HEADERS), timeout=20))
    return s["attributes"].get(attr) if attr else s["state"]


async def main():
    post("timer/start", {"entity_id": "timer.temporizador_2", "duration": 90})
    await asyncio.sleep(1)

    cli = APIClient("192.168.31.135", 6053, None, noise_psk=CHAVE)
    await cli.connect(login=True)
    ents, _ = await cli.list_entities_services()
    k = next(e.key for e in ents if getattr(e, "name", "") == "Depuracao contagem")
    linhas = []
    cli.subscribe_states(lambda s: linhas.append(getattr(s, "state", "")) if s.key == k else None)
    await asyncio.sleep(1)

    post("media_player/play_media",
         {"entity_id": "media_player.mini_tv_painel_de_voz",
          "media_content_id": "http://192.168.31.180:8123/local/sons/alarme_atual.wav",
          "media_content_type": "music"})
    await asyncio.sleep(4)
    print("a tocar -> titulo no painel:", repr(st("text.mini_tv_titulo_do_media")),
          "| ultimo estado:", linhas[-1] if linhas else None)
    await asyncio.sleep(9)
    print("depois de acabar ->", linhas[-1] if linhas else None)
    await cli.disconnect()
    post("timer/cancel", {"entity_id": "timer.temporizador_2"})


asyncio.run(main())
