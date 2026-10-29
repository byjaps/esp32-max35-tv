"""Automação única para o título do painel de voz.

Ordem de precedência:
  1. Music Assistant com metadados frescos (é quem sabe o nome da estação/faixa);
  2. chamada directa `play_media` ao painel (pelo HA) -> nome derivado do URL;
  3. nada a tocar -> limpa.

Porquê juntar: duas automações (uma do URL, uma do MA) escreviam uma por cima da
outra e ficava sempre o nome da última coisa que tocou.
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

VALOR = (
    f"{{% set painel = '{PAINEL}' %}}"
    f"{{% set ma = '{MA}' %}}"
    "{% set st = states(painel) %}"
    "{% set idade = (as_timestamp(now()) - as_timestamp(states[ma].last_updated)) "
    "if states[ma] is not none else 999999 %}"
    "{% set t_ma = state_attr(ma, 'media_title') or '' %}"
    "{% set a_ma = state_attr(ma, 'media_artist') or '' %}"
    "{% if st not in ['playing','announcing','paused','buffering'] %}"
    "{% elif states(ma) in ['playing','paused'] and t_ma and idade < 180 %}"
    "{{ (t_ma ~ ' · ' ~ a_ma) if a_ma and a_ma not in t_ma else t_ma }}"
    "{% elif trigger.platform == 'event' %}"
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
    "{% set ns.v = cid.split('//')[-1].split('/')[0].split(':')[0] | lower | replace('www.', '') %}"
    "{% set ns.v = ns.v | replace('-', ' ') | title %}"
    "{% endif %}"
    "{{ ns.v | trim }}"
    "{% endif %}"
)

auto = {
    "id": "hermes_painel_titulo_ma",
    "alias": "Hermes - Painel: nome do que esta a tocar",
    "description": (
        "Escreve text.mini_tv_titulo_do_media com o nome do que toca. Precedencia: "
        "metadados do Music Assistant (frescos) > nome derivado do URL de um "
        "play_media directo. Substitui a automacao 1789242899374."
    ),
    "mode": "restart",
    "trigger": [
        {"platform": "event", "event_type": "call_service",
         "event_data": {"domain": "media_player", "service": "play_media"}},
        {"platform": "state", "entity_id": players, "attribute": "media_title"},
        {"platform": "state", "entity_id": PAINEL},
    ],
    "condition": [],
    "action": [
        {"condition": "template",
         "value_template": (
             "{% set cid = trigger.event.data.service_data.media_content_id | default('', true) | string "
             "if trigger.platform == 'event' else '' %}"
             "{{ '/local/sons/' not in cid }}")},
        {"service": "text.set_value",
         "target": {"entity_id": "text.mini_tv_titulo_do_media"},
         "data": {"value": VALOR}},
    ],
}

rq = urllib.request.Request(
    f"{BASE}/api/config/automation/config/{auto['id']}",
    data=json.dumps(auto).encode(), headers=HEADERS, method="POST")
with urllib.request.urlopen(rq, timeout=30) as r:
    print("automação única:", r.status, r.read().decode()[:60])
print("players vigiados:", len(players))
