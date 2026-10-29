"""Automação única do título do painel — versão com dois ramos explícitos.

  * play_media directo ao painel (pelo HA) -> nome derivado do URL, escrito na hora.
  * qualquer outra mudança de estado -> metadados do Music Assistant, mas só se
    forem frescos (senão ficava o nome da última coisa que tocou).
  * nada a tocar -> limpa.
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

PAINEL = "media_player.mini_tv_painel_de_voz"
MA = "media_player.mini_tv_painel_de_voz_2"

states = json.load(urllib.request.urlopen(
    urllib.request.Request(f"{BASE}/api/states", headers=HEADERS), timeout=30))
players = [s["entity_id"] for s in states if s["entity_id"].startswith("media_player.")]

# --- ramo 1: nome a partir do URL de um play_media directo
DO_URL = (
    "{% set cid = trigger.event.data.service_data.media_content_id | default('', true) | string %}"
    "{% set c = cid | lower %}"
    "{% set mapa = {'noite': 'Noite FM', 'rfm': 'RFM', 'comercial': 'Radio Comercial',"
    " 'antena1': 'Antena 1', 'antena2': 'Antena 2', 'antena3': 'Antena 3',"
    " 'megahits': 'Mega Hits', 'mega hits': 'Mega Hits', 'cidade': 'Cidade FM',"
    " 'renascenca': 'Radio Renascenca', 'observador': 'Observador', 'tsf': 'TSF',"
    " 'spotify': 'Spotify', 'youtube': 'YouTube', 'radio_browser': ''} %}"
    "{% set ns = namespace(v='') %}"
    "{% for k, v in mapa.items() %}{% if k in c and ns.v == '' %}{% set ns.v = v %}{% endif %}{% endfor %}"
    "{% if ns.v == '' and 'media-source://' in c %}"
    "{% set seg = cid.split('/')[-1].split('?')[0] | replace('%20', ' ') | replace('%22', '') | replace('+', ' ') %}"
    "{% set limpo = seg | replace('_', ' ') | replace('.mp3', '') | replace('.m3u8', '') | trim %}"
    "{% if (limpo | length) == 36 and (limpo.split('-') | length) == 5 %}{% set limpo = '' %}{% endif %}"
    "{% if (limpo | length) > 1 %}{% set ns.v = limpo %}{% endif %}"
    "{% endif %}"
    "{% if ns.v == '' and '//' in cid %}"
    "{% set host = cid.split('//')[-1].split('/')[0].split(':')[0] | lower | replace('www.', '') %}"
    "{% if host.split('.')[-1] | int(-1) == -1 %}{% set ns.v = host.split('.')[-2] | replace('-', ' ') | title %}"
    "{% else %}{% set ns.v = 'Radio' %}{% endif %}"
    "{% endif %}"
    "{{ ns.v | trim }}"
)

# --- ramo 2: metadados do Music Assistant, só se frescos (< 90 s)
DO_MA = (
    f"{{% set painel = '{PAINEL}' %}}"
    f"{{% set ma = '{MA}' %}}"
    "{% set idade = (as_timestamp(now()) - as_timestamp(states[ma].last_updated)) "
    "if states[ma] is not none else 999999 %}"
    "{% set t = state_attr(ma, 'media_title') or '' %}"
    "{% set a = state_attr(ma, 'media_artist') or '' %}"
    "{% if states(painel) not in ['playing','announcing','paused','buffering'] %}"
    "{% elif states(ma) in ['playing','paused'] and t and idade < 90 %}"
    "{{ (t ~ ' · ' ~ a) if a and a not in t else t }}"
    "{% endif %}"
)

set_titulo = {"service": "text.set_value",
              "target": {"entity_id": "text.mini_tv_titulo_do_media"},
              "data": {"value": DO_URL}}

set_ma = {"service": "text.set_value",
          "target": {"entity_id": "text.mini_tv_titulo_do_media"},
          "data": {"value": DO_MA}}

auto = {
    "id": "hermes_painel_titulo_ma",
    "alias": "Hermes - Painel: nome do que esta a tocar",
    "description": (
        "Nome do que toca em text.mini_tv_titulo_do_media. Ramo 1: play_media "
        "directo ao painel -> nome derivado do URL. Ramo 2: metadados do Music "
        "Assistant quando frescos. Substitui a automacao 1789242899374."
    ),
    "mode": "queued",
    "max": 10,
    "trigger": [
        {"platform": "event", "event_type": "call_service",
         "event_data": {"domain": "media_player", "service": "play_media"}},
        {"platform": "state", "entity_id": players, "attribute": "media_title"},
        {"platform": "state", "entity_id": PAINEL},
    ],
    "condition": [],
    "action": [
        {"if": [
            {"condition": "template",
             "value_template": (
                 "{% set cid = trigger.event.data.service_data.media_content_id | default('', true) | string %}"
                 "{{ trigger.platform == 'event'"
                 " and 'media_player.mini_tv_painel_de_voz' in (trigger.event.data.service_data.entity_id | default('', true) | string)"
                 " and '/local/sons/' not in cid }}")},
         ],
         "then": [set_titulo],
         "else": [set_ma]},
    ],
}

rq = urllib.request.Request(
    f"{BASE}/api/config/automation/config/{auto['id']}",
    data=json.dumps(auto).encode(), headers=HEADERS, method="POST")
with urllib.request.urlopen(rq, timeout=30) as r:
    print("automação v3:", r.status, r.read().decode()[:60])
