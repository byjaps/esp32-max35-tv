#!/usr/bin/env python3
"""Probe the panel over the ESPHome native API.

Prints device info (project version + compilation time), the entity list and
live log lines. This is the honest way to confirm which firmware is actually
running (a successful OTA can silently roll back) and to watch button
gestures / wake word while someone tests against the board.

Usage:
    python3 verifica-painel.py <seconds> [host]

Host defaults to the PANEL_HOST env var (see _panel_config.py).

Notes for this ESPHome version:
- `cli.subscribe_logs(...)` returns a partial (do NOT await it; keep the loop
  alive with asyncio.sleep).
- The log message arrives as bytes: decode with `msg.message.decode()`.
- `device_info().project_version` + `.compilation_time` is the only reliable
  proof of what is running.
"""
import asyncio
import sys

import aioesphomeapi

from _panel_config import PANEL_HOST, PANEL_PORT, PANEL_API_KEY, require_panel


async def main(seconds):
    require_panel()
    host = sys.argv[2] if len(sys.argv) > 2 else PANEL_HOST
    cli = aioesphomeapi.APIClient(host, PANEL_PORT, None, noise_psk=PANEL_API_KEY)
    await cli.connect(login=True)

    info = await cli.device_info()
    print(f"device: {info.name} | version: {info.project_version} | "
          f"compiled: {info.compilation_time}")

    entidades = await cli.list_entities_services()
    nomes = [e.name for e in entidades[0] if getattr(e, "name", "")]
    for n in sorted(nomes):
        print("  -", n)
    print("--- log (Ctrl-C to stop) ---")

    def on_log(msg):
        m = getattr(msg, "message", None)
        if m is None:
            return
        if isinstance(m, bytes):
            m = m.decode("utf-8", errors="replace")
        print(m.rstrip())

    # this aioesphomeapi version returns a partial (not awaited): call and keep
    # the loop alive.
    cli.subscribe_logs(on_log, log_level=7)
    await asyncio.sleep(seconds)
    await cli.disconnect()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20))