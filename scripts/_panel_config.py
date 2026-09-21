#!/usr/bin/env python3
"""Shared config for the panel helper scripts.

Reads connection settings from environment variables (preferred) or from a
local `secrets.yaml` (kept out of git). Nothing is hard-coded to a personal
network or to Home Assistant.

Environment variables:
  PANEL_HOST   ESPHome panel IP or hostname (e.g. 192.168.1.50 or panel.local)
  PANEL_API_KEY  the ESPHome `api: encryption: key` (from secrets.yaml)
  HA_URL       Home Assistant base URL, e.g. http://homeassistant.local:8123
  HA_TOKEN     Home Assistant long-lived access token

Alternatively, place a `secrets.yaml` next to these scripts with:
  panel_host: ...
  api_encryption_key: ...
  ha_url: ...
  ha_token: ...
"""
import os

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def _from_env(name, default=None):
    return os.environ.get(name, default)


def _load_secrets():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "secrets.yaml")
    if yaml is not None and os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


_SECRETS = _load_secrets()

# ESPHome panel connection
PANEL_HOST = _from_env("PANEL_HOST", _SECRETS.get("panel_host"))
PANEL_PORT = int(_from_env("PANEL_PORT", "6053"))
PANEL_API_KEY = _from_env("PANEL_API_KEY", _SECRETS.get("api_encryption_key"))

# Home Assistant REST
_ha_url = _from_env("HA_URL")
if not _ha_url:
    _ha_url = _SECRETS.get("ha_url") or ""
HA_URL = str(_ha_url).rstrip("/")
HA_TOKEN = _from_env("HA_TOKEN", _SECRETS.get("ha_token"))


def require_panel():
    if not PANEL_HOST:
        raise SystemExit("PANEL_HOST is not set (or missing in secrets.yaml)")
    if not PANEL_API_KEY:
        raise SystemExit("PANEL_API_KEY is not set (or missing in secrets.yaml)")