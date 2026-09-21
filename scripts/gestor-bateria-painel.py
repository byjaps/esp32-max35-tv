#!/usr/bin/env python3
"""Battery discharge/recharge test manager for the MAX35-TV panel.

Periodically:
 1. reads the panel battery (native ESPHome API) and the state of a charge
    plug in HA (REST);
 2. appends a row to `dados/battery-panel.csv` (the test curve);
 3. SAFETY - if the plug is OFF and the battery is at or below a floor, or the
    panel does not answer (brownout/reboot), it turns the plug ON and prints a
    message (in a no_agent cron, stdout is delivered; empty = silence).

The charge plug is a configurable HA switch - set it with the PLUG_ENTITY env
var (default: none, safety control disabled). This is a generic version; your
personal charging automation lives outside this repo.

Usage: python3 gestor-bateria-painel.py
"""
import asyncio
import csv
import datetime as dt
import json
import os
import sys
import urllib.request

import aioesphomeapi

from _panel_config import (PANEL_HOST, PANEL_PORT, PANEL_API_KEY, HA_URL,
                           HA_TOKEN, require_panel)

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "dados", "battery-panel.csv")
PLUG_ENTITY = os.environ.get("PLUG_ENTITY", "")   # e.g. switch.charge_plug

# Stop level of the discharge test: below this, turn the plug back on.
# Do not go to the 0% of the scale (3.30 V): at the bottom the curve is a
# cliff and 5-min samples could catch a brownout (reboot) instead of clean data.
# 3.40 V (~11%) already gives the bottom of the curve, which is the part worth
# calibrating.
LIMITE_V = 3.40          # ~11% on the panel scale ((v-3.30)/0.90*100)
PANEL_TIMEOUT = 15.0


def _ha_headers():
    if not HA_TOKEN:
        raise SystemExit("HA_TOKEN is not set (or missing in secrets.yaml)")
    return {"Authorization": f"Bearer {HA_TOKEN}"}


async def le_painel():
    """Return (voltage, percent, usb, charger) or None if the panel does not answer."""
    require_panel()
    cli = aioesphomeapi.APIClient(PANEL_HOST, PANEL_PORT, None, noise_psk=PANEL_API_KEY)
    try:
        await asyncio.wait_for(cli.connect(login=True), PANEL_TIMEOUT)
        entidades, _ = await cli.list_entities_services()
        nomes = {e.key: (e.name or "").lower() for e in entidades}
        alvos = {k: n for k, n in nomes.items()
                 if n in ("bateria tens\u00e3o", "bateria", "usb tens\u00e3o", "carregador ligado")}
        lido = {}

        def on_state(st):
            if st.key in alvos:
                lido[alvos[st.key]] = st.state

        cli.subscribe_states(on_state)
        await asyncio.sleep(6)
        return (lido.get("bateria tens\u00e3o"), lido.get("bateria"),
                lido.get("usb tens\u00e3o"), lido.get("carregador ligado"))
    except Exception:
        return None
    finally:
        try:
            await cli.disconnect()
        except Exception:
            pass


def ha_get(ent):
    req = urllib.request.Request(f"{HA_URL}/api/states/{ent}", headers=_ha_headers())
    return json.load(urllib.request.urlopen(req, timeout=20))


def ha_post(servico, dados):
    req = urllib.request.Request(
        f"{HA_URL}/api/services/{servico}",
        data=json.dumps(dados).encode(),
        headers={**_ha_headers(), "Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=25).read().decode()


def main():
    lido = asyncio.run(le_painel())

    tomada_on = None
    watts = None
    if PLUG_ENTITY:
        tomada_on = ha_get(PLUG_ENTITY)["state"] == "on"
        try:
            watts = float(ha_get(f"{PLUG_ENTITY}_potencia")["state"])
        except Exception:
            watts = None

    agora = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    linha = [agora, "", "", "", "", "on" if tomada_on else ("off" if tomada_on is not None else ""),
             f"{watts:.1f}" if watts is not None else ""]
    if lido:
        v, pct, usb, chg = lido
        linha[1] = f"{v:.3f}" if isinstance(v, float) else ""
        linha[2] = f"{pct:.1f}" if isinstance(pct, float) else ""
        linha[3] = f"{usb:.3f}" if isinstance(usb, float) else ""
        linha[4] = "on" if chg is True else ("off" if chg is False else "")

    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    novo = not os.path.exists(CSV)
    with open(CSV, "a", newline="") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["ts_iso", "voltage_V", "percent", "usb_V", "charger", "plug", "plug_W"])
        w.writerow(linha)

    if not PLUG_ENTITY:
        return  # safety control disabled (no plug entity configured)

    # ---------------- safety: put it on charge ----------------
    if tomada_on:
        return  # already charging: nothing to do, silence
    if lido is None:
        ha_post("switch/turn_on", {"entity_id": PLUG_ENTITY})
        print("Panel did not answer (low battery/reboot). "
              "Turned the charge plug ON so it does not run out.")
        return
    v = lido[0]
    if isinstance(v, float) and v <= LIMITE_V:
        ha_post("switch/turn_on", {"entity_id": PLUG_ENTITY})
        pct = lido[1]
        print(f"End of discharge test: battery at {v:.3f} V"
              + (f" ({pct:.0f} %)" if isinstance(pct, float) else "")
              + ". Turned the charge plug ON - it will start charging.")


if __name__ == "__main__":
    main()