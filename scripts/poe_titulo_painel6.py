"""Automação do título do painel — v5 (a que resolve os dois casos).

O problema: a entidade `_2` do Music Assistant **espelha** o que o painel toca.
Ao mandar tocar pelo Radio Browser, o MA também a atualiza, mas com o título
VELHO (não sabe resolver aquele stream) — e ganhava ao nome tirado do URL.

Solução: ao receber um `play_media`, guarda o título que o MA tinha, escreve já o
nome derivado do URL e, 4 s depois, só troca para o título do MA se ele **mudou**
nesse intervalo (sinal de que o MA soube mesmo o que está a tocar).
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/hermes/.hermes/scripts")
from ha_env import BASE, HEADERS  # noqa: E402

PAINEL = "media_player.mini_tv_painel_de_voz"
MA = "media_player.mini_tv_painel_de_voz_2"
TITULO = "text.mini_tv_titulo_do_media"

states = json.load(urllib.request.urlopen(
    urllib.request.Request(f"{BASE}/api/states", headers=HEADERS), timeout=30))
players = [s["entity_id"] for s in states if s["entity_id"].startswith("media_player.")]

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
    "{% if (host.split('.')[-1] | int(-1)) != -1 %}{% set ns.v = 'Radio' %}"
    "{% else %}{% set ns.v = host.split('.')[-2] | replace('-', ' ') | title %}{% endif %}"
    "{% endif %}"
    "{{ ns.v | trim }}"
)

# Título do MA (+ artista), usado depois do atraso de 4 s
DO_MA = (
    f"{{% set ma = '{MA}' %}}"
    "{% set t = state_attr(ma, 'media_title') or '' %}"
    "{% set a = state_attr(ma, 'media_artist') or '' %}"
    "{{ (t ~ ' · ' ~ a) if a and a not in t else t }}"
)

auto = {
    "id": "hermes_painel_titulo_ma",
    "alias": "Hermes - Painel: nome do que esta a tocar",
    "description": (
        "Nome do que toca em text.mini_tv_titulo_do_media. Ao mandar tocar: escreve "
        "ja o nome derivado do URL e, 4 s depois, troca para o titulo do Music "
        "Assistant SE ele tiver mudado (senao era o nome anterior). Limpa ao parar."
    ),
    "mode": "queued",
    "max": 10,
    "trigger": [
        {"platform": "event", "event_type": "call_service",
         "event_data": {"domain": "media_player", "service": "play_media"}},
        {"platform": "state", "entity_id": [MA], "attribute": "media_title"},
        {"platform": "state", "entity_id": [PAINEL]},
    ],
    "condition": [],
    "action": [
        {"choose": [
            {"conditions": [
                {"condition": "template",
                 "value_template": (
                     "{% set cid = trigger.event.data.service_data.media_content_id | default('', true) | string %}"
                     "{{ trigger.platform == 'event'"
                     " and 'media_player.mini_tv_painel_de_voz' in (trigger.event.data.service_data.entity_id | default('', true) | string)"
                     " and '/local/sons/' not in cid }}")}],
             "sequence": [
                 {"variables": {"nome_url": DO_URL}},
                 {"service": "text.set_value",
                  "target": {"entity_id": TITULO},
                  "data": {"value": "{{ nome_url }}"}},
                 {"delay": "00:00:04"},
                 # Só se aceita o título do MA quando o URL não deu nome nenhum
                 # («Radio»): o MA espelha o painel e, quando não sabe resolver o
                 # stream, devolve o nome da estação ANTERIOR.
                 {"if": [
                     {"condition": "template",
                      "value_template": (
                          "{% set agora = state_attr('" + MA + "', 'media_title') | default('') %}"
                          "{{ (nome_url | trim) in ['', 'Radio'] and agora"
                          " and states('" + PAINEL + "') in ['playing','announcing','paused','buffering'] }}")}],
                  "then": [
                      {"service": "text.set_value",
                       "target": {"entity_id": TITULO},
                       "data": {"value": DO_MA}}]},
             ]},
            {"conditions": [
                {"condition": "template",
                 "value_template": (
                     "{{ trigger.platform == 'state' and trigger.to_state is not none"
                     " and trigger.to_state.entity_id == '" + MA + "'"
                     " and states('" + PAINEL + "') in ['playing','announcing','paused','buffering']"
                     " and (as_timestamp(now()) - as_timestamp(states['" + PAINEL + "'].last_changed)) > 6 }}")}],
             "sequence": [
                 {"service": "text.set_value",
                  "target": {"entity_id": TITULO},
                  "data": {"value": DO_MA}}]},
            {"conditions": [
                {"condition": "template",
                 "value_template": (
                     "{{ trigger.platform == 'state' and trigger.to_state is not none"
                     " and trigger.to_state.entity_id == '" + PAINEL + "'"
                     " and trigger.to_state.state not in ['playing','announcing','paused','buffering'] }}")}],
             "sequence": [
                 {"service": "text.set_value",
                  "target": {"entity_id": TITULO},
                  "data": {"value": ""}}]},
        ]},
    ],
}

rq = urllib.request.Request(
    f"{BASE}/api/config/automation/config/{auto['id']}",
    data=json.dumps(auto).encode(), headers=HEADERS, method="POST")
with urllib.request.urlopen(rq, timeout=30) as r:
    print("automação v5:", r.status, r.read().decode()[:60])

rq2 = urllib.request.Request(f"{BASE}/api/services/automation/reload", data=b"{}",
                             headers=HEADERS, method="POST")
print("reload:", urllib.request.urlopen(rq2, timeout=60).status)
