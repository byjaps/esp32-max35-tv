#!/usr/bin/env python3
"""Sample the panel battery voltage over the native API, every N seconds.

Writes one line per sample (time, V, %) to a log file. Use it to watch the
TREND: with the charger connected the voltage must rise; if it stays flat or
drops, the charger is not charging.

Usage: python3 vigia-bateria.py <minutes> [seconds_between_samples] [host]
"""
import asyncio
import os
import sys
import time

import aioesphomeapi

from _panel_config import PANEL_HOST, PANEL_PORT, PANEL_API_KEY, require_panel

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados", "battery-watch.log")


async def main(minutos, passo):
    require_panel()
    host = sys.argv[3] if len(sys.argv) > 3 else PANEL_HOST
    cli = aioesphomeapi.APIClient(host, PANEL_PORT, None, noise_psk=PANEL_API_KEY)
    await cli.connect(login=True)
    entidades, _ = await cli.list_entities_services()
    chaves = {}
    for e in entidades:
        n = (e.name or "").lower()
        if n == "bateria tens\u00e3o":
            chaves[e.key] = "V"
        elif n == "bateria":
            chaves[e.key] = "%"
        elif n == "usb tens\u00e3o":
            chaves[e.key] = "usb"
    valores = {}

    def on_state(st):
        u = chaves.get(st.key)
        if u:
            valores[u] = st.state

    cli.subscribe_states(on_state)
    await asyncio.sleep(5)
    fim = time.time() + minutos * 60
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"\n--- start {time.strftime('%H:%M:%S')} ---\n")
        while time.time() < fim:
            linha = (f"{time.strftime('%H:%M:%S')}  "
                     f"{valores.get('V', float('nan')):.3f} V  "
                     f"{valores.get('%', float('nan')):.0f}%  "
                     f"usb={valores.get('usb', float('nan')):.2f} V")
            print(linha, flush=True)
            f.write(linha + "\n")
            f.flush()
            await asyncio.sleep(passo)
    await cli.disconnect()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 10,
                     int(sys.argv[2]) if len(sys.argv) > 2 else 30))