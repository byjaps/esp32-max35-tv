#!/usr/bin/env python3
"""Sample the panel battery once and append a row to a CSV.

Reads LIVE from the ESPHome native API, because the firmware filters/throttle
delay publication to HA by up to ~2.5 min.

Usage: python3 regista-bateria.py [host]
Output: data/battery-panel.csv -> ts_iso,voltage_V,percent,usb_V,charger

Runs from the script's directory; a `dados/` subfolder is created on first run.
"""
import asyncio
import csv
import datetime as dt
import os
import sys

import aioesphomeapi

from _panel_config import PANEL_HOST, PANEL_PORT, PANEL_API_KEY, require_panel

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "dados", "battery-panel.csv")

# NOTE: the entity names in ESPHome contain accented chars (e.g. "Bateria Tens\u00e3o"
# -> "bateria tens\u00e3o", compared lowercased and exact) - a wrong accent writes empty cells.
QUERO = {
    "bateria tens\u00e3o": "v",
    "bateria": "pct",
    "usb tens\u00e3o": "usb",
    "carregador ligado": "chg",
}


async def main():
    require_panel()
    host = sys.argv[1] if len(sys.argv) > 1 else PANEL_HOST
    cli = aioesphomeapi.APIClient(host, PANEL_PORT, None, noise_psk=PANEL_API_KEY)
    await cli.connect(login=True)
    entidades, _ = await cli.list_entities_services()
    nomes = {e.key: (e.name or "").lower() for e in entidades}
    alvos = {k: QUERO[n] for k, n in nomes.items() if n in QUERO}
    lido = {}

    def on_state(st):
        campo = alvos.get(st.key)
        if campo:
            lido[campo] = st.state

    cli.subscribe_states(on_state)
    await asyncio.sleep(6)  # time for one value per sensor to arrive
    await cli.disconnect()

    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    novo = not os.path.exists(CSV)
    with open(CSV, "a", newline="") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["ts_iso", "voltage_V", "percent", "usb_V", "charger"])
        agora = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        w.writerow([
            agora,
            f"{lido.get('v', float('nan')):.3f}" if isinstance(lido.get("v"), float) else lido.get("v", ""),
            f"{lido.get('pct'):.1f}" if isinstance(lido.get("pct"), float) else lido.get("pct", ""),
            f"{lido.get('usb'):.3f}" if isinstance(lido.get("usb"), float) else lido.get("usb", ""),
            "on" if lido.get("chg") is True else ("off" if lido.get("chg") is False else ""),
        ])
    # no print: when run from cron with no_agent, empty stdout = no noise


if __name__ == "__main__":
    asyncio.run(main())