#!/usr/bin/env python3
"""Read the panel's current entity states live over the ESPHome native API.

Useful for seeing up-to-the-second values without waiting for the firmware
filters/throttle that delay publication to HA (e.g. USB voltage only republishes
every ~2.5 min).

Usage: python3 le-estado.py [seconds] [host]

Host defaults to PANEL_HOST (see _panel_config.py).
"""
import asyncio
import sys

import aioesphomeapi

from _panel_config import PANEL_HOST, PANEL_PORT, PANEL_API_KEY, require_panel

QUERO = ("usb", "bateria", "carregador", "uptime", "volume", "fps")


async def main(segs):
    require_panel()
    host = sys.argv[2] if len(sys.argv) > 2 else PANEL_HOST
    cli = aioesphomeapi.APIClient(host, PANEL_PORT, None, noise_psk=PANEL_API_KEY)
    await cli.connect(login=True)
    entidades, _ = await cli.list_entities_services()
    nomes = {e.key: e.name for e in entidades}
    alvos = {k: n for k, n in nomes.items() if any(q in (n or "").lower() for q in QUERO)}

    def on_state(st):
        nome = alvos.get(st.key)
        if nome:
            print(f"{nome:28} = {st.state}")

    cli.subscribe_states(on_state)
    await asyncio.sleep(3)
    print(f"--- watching {segs}s (plug/unplug the charger now) ---")
    await asyncio.sleep(segs)
    await cli.disconnect()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 30))