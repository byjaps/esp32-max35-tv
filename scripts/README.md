# Scripts

Helpers for working with the panel. They talk to the board over the ESPHome
native API (`aioesphomeapi`, ships with ESPHome) or to Home Assistant. They are
kept generic — where they need the board's IP / HA details, provide them via
environment or command-line args (see each file's header); nothing hard-codes a
personal network.

| Script | What it does |
|---|---|
| `verifica-painel.py <seconds>` | Poll the board: device info (project version + compilation time), entity list and live log — the honest way to confirm what firmware is actually running and watch gestures/wake word. |
| `le-estado.py` | Read the current value of a few HA entities via REST. |
| `vigia-bateria.py <minutes>` | Sample the battery every 30 s and watch the trend (charging → voltage must rise). |
| `regista-bateria.py` | Log battery values over time. |
| `gestor-bateria-painel.py` | Battery logger + optional charge-plug safety (set `PLUG_ENTITY`). |
| `mockup_render.py` | Render the HUD to PNG offline (Python/PIL) with the same drawing primitives — so a screen change is seen & approved before a ~10 min compile+OTA. |

Wake-word model changes are done directly in the YAML (see `docs/wake-word.md`);
the one-off migration scripts that used to patch the old config are not
included here.

## Notes

- `verifica-painel.py`'s log subscription quirk on this ESPHome version:
  `subscribe_logs` returns a partial (do not await it — keep the loop alive),
  and the message arrives as `bytes` (`msg.message.decode()`).
- Board build info from `device_info().project_version` + `compilation_time` is
  the only honest way to know the running binary matches the freshly compiled
  OTA.