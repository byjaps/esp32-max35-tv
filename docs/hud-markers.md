# HUD text written by the agent (markers)

The panel can show **one line of text on its screen** that is *never spoken aloud*.
The agent decides what it says by embedding a marker in its reply; the Home Assistant
conversation component strips the marker out of the speech and writes the text into the
`Linha HUD` entity, and the firmware draws it.

Feature version: **v0.15.16** (line), **v0.15.17** (auto-clear).
Requires a **local patch** on the Hermes HA component — see [Install](#install).

## Why it lives in Home Assistant, not on the panel

The panel never sees text: it receives **audio** and state events from the Assist
pipeline. By the time the reply leaves Home Assistant it is already speech, so the only
place that can remove something from it *before* text-to-speech is the conversation
component. The firmware only receives "here is a string to draw".

```
Agent reply (text)                         HA conversation component            Panel
"[HW:/display/info:{\"text\":\"23:45\"}] Boa noite."
        │                                            │
        ├─ markers extracted, speech = "Boa noite." ─┼──→ TTS ─────────────────→ 🔊
        └─ text.set_value(text.mini_tv_linha_hud,"23:45") ──────────────────────→ 🖥
```

## Marker format

```
[HW:<route>]                      e.g. [HW:/light]
[HW:<route>:<json object>]        e.g. [HW:/light:{"brightness_pct": 40}]
```

- Anywhere in the reply; several markers per reply are allowed.
- The whole marker is removed from the spoken text, **always** — even when the route is
  unknown or the JSON is broken. A marker is never read out loud (that was the design
  rule: clean first, execute only what parses).
- If a reply consists *only* of markers, the panel says `Feito.` instead of going silent.

## Routes implemented

| Marker | Home Assistant service | Notes |
|---|---|---|
| `/display/info` | `text.set_value` on `text.mini_tv_linha_hud` | `{"text": "..."}`, max 60 chars; firmware truncates to 20 (ring) / 14 (media screen) |
| `/light` | `light.turn_on` on the screen light | `{"brightness_pct": 0-100}` |
| `/volume` | `number.set_value` on the panel volume | `{"value": 0-100}` |

Entity names are deployment-specific — read them from **Developer tools → States**
before editing the route table in `hw_markers.py`. On this installation the panel mixes
prefixes (`light.mini_tv_assistente_22a058_ecra` next to `text.mini_tv_linha_hud`), which
is exactly the kind of thing to check rather than guess.

## Behaviour on screen

- Empty entity → **nothing is drawn**; the screen is identical to a firmware without this
  feature.
- Drawn inside the state ring at `(240, 205)` and, on the media screen, in the right-hand
  column.
- **v0.15.17**: the line disappears **45 s** after it was written (each new value restarts
  the count) and is cleared **when a new wake word opens the microphone**, so the previous
  answer never sits on screen during the next question.

## Install

The marker handling is a **local patch** on
[`rusty4444/hermes-voice-ha-integration`](https://github.com/rusty4444/hermes-voice-ha-integration)
v0.0.15 — it is not upstream. Files in [`hermes/`](hermes/):

- `hud-markers/hw_markers.py` → `/config/custom_components/hermes/hw_markers.py`
- `conversation.py.diff` → three additions to `conversation.py` (import, marker strip +
  dispatch after the reply, and the per-turn convention)

```bash
# on the Home Assistant host (core-ssh add-on)
cd /config/custom_components/hermes
cp conversation.py conversation.py.bak        # keep the original
patch -p0 conversation.py < conversation.py.diff   # or apply the three blocks by hand
# copy hw_markers.py next to it, then restart Home Assistant
```

Verify after restart: ask for something that produces a marker and confirm the reply is
spoken **without** the marker and the value appears in `text.mini_tv_linha_hud`.

> An HACS update of the component overwrites `conversation.py` and the strip silently
> disappears (the marker is then read aloud). Re-apply the patch after every component
> update, and keep `hw_markers.py` in place.

## The convention sent to the agent

The component only adds the instruction **on turns that come from this panel**
(device registry name/model contains `max35` or `mini tv`, or the satellite id matches).
Other conversation channels and the local intents fast path are untouched — prefixing the
text there would break intent matching.

```
Convenção do painel de voz: se a resposta tiver de mostrar algo no ecrã, começa com
[HW:/display/info:{"text":"..."}] (máx. 60 caracteres, sem repetir o que dizes em voz
alta) e depois o texto normal. O marcador não é falado.
```

## Testing without speaking to the panel

A WebSocket `assist_pipeline/run` with `input.text` does **not** carry a `device_id`, so
the convention is not applied — that is expected, not a bug. To test the strip and the
drawing end-to-end, send a marker explicitly:

```bash
curl -s -X POST http://homeassistant:8123/api/conversation/process \
  -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"Responde só com: [HW:/display/info:{\"text\":\"TESTE\"}] Feito.","agent_id":"conversation.hermes"}'
```

The reply must be `Feito.` and the entity must read `TESTE`.

## Limits (enforced below the agent)

Safety is not something you ask a language model for. `hw_markers.py` carries a `LIMITES`
table and a pure `_limitar()` applied right before the service call:

| Route | Field | Day | 23:00-08:00 |
|---|---|---|---|
| `/light` | `brightness_pct` | 0-100 | **max 15** |
| `/volume` | `value` | **max 80** | **max 35** |

- Invalid values (`"alto"`) are dropped with a log line; below-minimum values are raised.
- `PANEL_RULE` tells the agent the *same* numbers, so it never announces a value the screen
  will not honour. `teste_hw_markers.py` fails if the two drift apart.
- The screen is otherwise respected as asked: one line, 60 characters (it is 480×320).

Measured on the real panel (24/10/2026, 01:35): marker asking for 100 % → `light` went
255 → **38/255 (15 %)**.

## Routes are validated at startup

`validar_rotas(hass)` runs once per process on the first marker and logs a WARNING for every
entity in `ROTAS` that does not exist. This is the cheap answer to a real failure: after a
firmware rename, a marker dies silently because the entity id changed (it happened on
23/10 with `text.mini_tv_linha_hud`).
