"""Automação: nome do que está a tocar no painel de voz (fonte: qualquer player
do Music Assistant), escrita em text.mini_tv_titulo_do_media.

Porquê alargar: o painel ESPHome só recebe o URL do stream; o título vive no
player do Music Assistant, que pode não ser o `..._2` do painel (depende de
como se manda tocar). Assim escolhe-se o player que está a tocar.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

PAINEL = "media_player.mini_tv_painel_de_voz"

states = json.load(urllib.request.urlopen(
    urllib.request.Request(f"{BASE}/api/states", headers=HEADERS), timeout=30))
players = [s["entity_id"] for s in states if s["entity_id"].startswith("media_player.")]

VALOR = (
    "{% set painel = '" + PAINEL + "' %}"
    "{% set cand = states.media_player"
    " | rejectattr('entity_id','eq', painel)"
    " | selectattr('state','eq','playing')"
    " | selectattr('attributes.media_title','defined')"
    " | rejectattr('attributes.media_title','eq','')"
    " | list %}"
    "{% set pref = cand | selectattr('entity_id','search','mini_tv_painel') | list %}"
    "{% set escolha = (pref if pref | count > 0 else cand) | first %}"
    "{% if states(painel) in ['playing','announcing','paused','buffering'] "
    "and escolha is defined %}"
    "{% set t = escolha.attributes.media_title %}"
    "{% set a = escolha.attributes.media_artist | default('') %}"
    "{{ (t ~ ' · ' ~ a) if a and a not in t else t }}"
    "{% else %}{% endif %}"
)

auto = {
    "id": "hermes_painel_titulo_ma",
    "alias": "Hermes - Painel: nome do que esta a tocar",
    "description": (
        "Escreve no painel (text.mini_tv_titulo_do_media) o titulo do que toca. "
        "O ESPHome so recebe o URL do stream (aparecia o IP do HA), por isso a "
        "fonte e o player do Music Assistant."
    ),
    "mode": "restart",
    "trigger": [
        {"platform": "state", "entity_id": players, "attribute": "media_title"},
        {"platform": "state", "entity_id": PAINEL},
    ],
    "condition": [],
    "action": [
        {"service": "text.set_value",
         "target": {"entity_id": "text.mini_tv_titulo_do_media"},
         "data": {"value": VALOR}},
    ],
}

rq = urllib.request.Request(
    f"{BASE}/api/config/automation/config/{auto['id']}",
    data=json.dumps(auto).encode(), headers=HEADERS, method="POST")
with urllib.request.urlopen(rq, timeout=30) as r:
    print("automação alargada:", r.status, r.read().decode()[:60])
print("players vigiados:", len(players))
