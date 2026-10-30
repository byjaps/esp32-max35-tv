"""[HW:...] markers in the agent reply -> actions on devices.

Convention (lampOS pattern, adapted): the agent writes, typically at the start of the
reply,

    [HW:/display/info:{"text":"14:30"}]
    [HW:/light:{"brightness_pct":40}]
    [HW:/volume:{"value":30}]

The marker is NOT spoken: it is extracted, translated into an HA service and removed
from the text before it reaches the TTS. It costs zero inference turns.

Rule from the 23/10/2026 trial: **clean first, run only what parses.**
The upstream strict regex does not catch JSON with a nested object; a marker that was
not caught ended up spoken aloud. Here the text is cleaned with the loose regex and
only the markers that pass `json.loads` are executed.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Canonical form: [HW:/route/sub:{"json"}] — body optional.
_HW_STRICT = re.compile(r"\[HW:((?:/[^{:\]]+(?::[^{:\]]+)*))(?::(\{[^}]*\}))?\]")
# Markdown link variant: [Lights off!](HW:/led/off:{}) -> marker + label.
_HW_LINK = re.compile(
    r"\[([^\]]*)\]\(\s*HW:\s*((?:/[^(){:\s]+(?::[^(){:\s]+)*))(?::(\{[^}]*\}))?:?\s*\)",
    re.I,
)
# Cleanup net: deletes ANYTHING shaped like a marker, even if invalid.
_HW_LOOSE = re.compile(r"\[HW:[^\]]*\]")

# ---------------------------------------------------------------------------
# Limits BELOW the agent (principle «safety is not asked of the model»).
# The prompt already tells the agent these numbers (PANEL_RULE); this is the last
# line of defence, in case it forgets or a request comes from somewhere else.
# Change here and in PANEL_RULE — both values must tell the same story.
# ---------------------------------------------------------------------------
# Usability floors MEASURED on the real panel (24/10/2026, 00:45):
# «the minimum volume to speak is 60 and the brightness 35; below that it is too low
# and too dark». Below this the panel is useless, so the floor is always guaranteed —
# by day and by night. These numbers are not personal taste: they were heard and seen.
QUIET_START, QUIET_END = 23, 8          # local hours of the HA instance
LIGHT_MIN, LIGHT_QUIET_MAX = 35, 70     # % brightness: floor 35, night ceiling 70
VOLUME_MIN, VOLUME_QUIET_MAX = 60, 70   # % volume: floor 60 (otherwise inaudible)
DAY_VOLUME_MAX = 90                     # daytime ceiling (the column is small)

# (route, field) -> (minimum, daytime maximum, night maximum)
LIMITES: dict[tuple[str, str], tuple[float, float, float]] = {
    ("/light", "brightness_pct"): (LIGHT_MIN, 100, LIGHT_QUIET_MAX),
    ("/volume", "value"): (VOLUME_MIN, DAY_VOLUME_MAX, VOLUME_QUIET_MAX),
}


def _em_quiet_hours(agora: datetime) -> bool:
    h = agora.hour
    return h >= QUIET_START or h < QUIET_END


def _limitar(
    rota: str, params: dict[str, Any], agora: datetime | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Clamps whatever goes over the limits. Returns (params, cuts). Pure function."""
    agora = agora or datetime.now()
    quiet = _em_quiet_hours(agora)
    cortes: list[str] = []
    dados = dict(params)
    for (r, campo), (minimo, max_dia, max_noite) in LIMITES.items():
        if r != rota or campo not in dados:
            continue
        try:
            valor = float(dados[campo])
        except (TypeError, ValueError):
            cortes.append(f"{campo} invalid ({dados[campo]!r}) — dropped")
            dados.pop(campo)
            continue
        teto = max_noite if quiet else max_dia
        if valor > teto:
            dados[campo] = int(teto) if float(teto).is_integer() else teto
            cortes.append(f"{campo} {valor:g}->{teto:g} ({'night' if quiet else 'day'})")
        elif valor < minimo:
            dados[campo] = minimo
            cortes.append(f"{campo} {valor:g}->{minimo:g} (minimum)")
    return dados, cortes


# Fallback text when the reply was ONLY markers (otherwise the TTS goes silent).
SPEECH_FALLBACK = "Feito."

# Supported routes. The entity must exist in HA; if it does not, the marker is
# dropped with a warning — a destination is never invented.
ROTAS: dict[str, tuple[str, str]] = {
    "/display/info": ("text.mini_tv_linha_hud", "texto"),
    "/light": ("light.mini_tv_assistente_22a058_ecra", "luz"),
    "/volume": ("number.mini_tv_volume_da_coluna", "numero"),
}


def _normalizar_links(texto: str) -> str:
    def _sub(m: re.Match[str]) -> str:
        label, rota, corpo = m.group(1), m.group(2), m.group(3) or "{}"
        marcador = f"[HW:{rota}:{corpo}]"
        if label[:3].lower() == "hw:":
            return f"[HW:{label[3:]}]" + marcador
        if not label.strip():
            return marcador
        return marcador + " " + label

    return _HW_LINK.sub(_sub, texto)


def extract_hw_markers(texto: str) -> tuple[list[tuple[str, dict[str, Any]]], str]:
    """Returns (valid calls, text with the markers stripped)."""
    if not texto or "[HW:" not in texto and "](HW:" not in texto:
        return [], texto

    texto = _normalizar_links(texto)
    chamadas: list[tuple[str, dict[str, Any]]] = []
    for m in _HW_STRICT.finditer(texto):
        rota = "/" + m.group(1).lstrip("/").replace(":", "/")
        corpo = m.group(2) or "{}"
        try:
            params = json.loads(corpo)
        except Exception:  # noqa: BLE001 - invalid marker: delete it, do not run it
            _LOGGER.warning("HW marker with invalid JSON at %s: %r", rota, corpo[:120])
            continue
        if not isinstance(params, dict):
            continue
        chamadas.append((rota, params))

    limpo = _HW_LOOSE.sub("", texto)
    limpo = re.sub(r"[ \t]{2,}", " ", limpo)
    limpo = re.sub(r"\n{3,}", "\n\n", limpo).strip()
    return chamadas, limpo


_rotas_verificadas = False


def validar_rotas(hass) -> list[str]:
    """Confirms that the ROTAS entities exist. Once per process.

    Without this, a new firmware that renames an entity leaves the marker dying
    silently (it happened on 23/10 with `text.mini_tv_linha_hud`). It fixes nothing:
    it reports what is missing, so that the table can be fixed.
    """
    global _rotas_verificadas
    faltam: list[str] = []
    if _rotas_verificadas:
        return faltam
    _rotas_verificadas = True
    for rota, (entidade, _tipo) in ROTAS.items():
        if hass.states.get(entidade) is None:
            faltam.append(entidade)
            _LOGGER.warning(
                "HW routes: entity %s (%s) does not exist — markers for that route "
                "are dropped until the ROTAS table is fixed",
                entidade,
                rota,
            )
    if not faltam:
        _LOGGER.debug("HW routes: %d routes checked, all present", len(ROTAS))
    return faltam


async def fire_hw_calls(hass, chamadas: list[tuple[str, dict[str, Any]]]) -> None:
    """Fires the actions. Fire-and-forget: a hardware failure never spoils the speech."""
    validar_rotas(hass)
    for rota, params in chamadas:
        destino = ROTAS.get(rota)
        if destino is None:
            _LOGGER.debug("HW marker with no mapped route: %s", rota)
            continue
        entidade, tipo = destino
        if hass.states.get(entidade) is None:
            _LOGGER.warning("HW marker %s: entity %s does not exist", rota, entidade)
            continue
        params, cortes = _limitar(rota, params)
        for corte in cortes:
            _LOGGER.info("HW limit applied on %s: %s", rota, corte)
        try:
            await _chamar(hass, entidade, tipo, params)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("HW marker %s failed on %s: %s", rota, entidade, exc)


async def _chamar(hass, entidade: str, tipo: str, params: dict[str, Any]) -> None:
    if tipo == "texto":
        valor = str(params.get("text", ""))
        sub = str(params.get("subtitle", "") or "")
        if sub:
            valor = f"{valor} — {sub}" if valor else sub
        await hass.services.async_call(
            "text", "set_value", {"entity_id": entidade, "value": valor[:60]}, blocking=False
        )
    elif tipo == "opcao":
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": entidade, "option": str(params.get("expression", ""))},
            blocking=False,
        )
    elif tipo == "luz":
        dados: dict[str, Any] = {"entity_id": entidade}
        if "brightness_pct" in params:
            dados["brightness_pct"] = max(0, min(100, int(params["brightness_pct"])))
        if "color" in params:
            dados["rgb_color"] = params["color"][:3]
        if params.get("off"):
            await hass.services.async_call("light", "turn_off", {"entity_id": entidade}, blocking=False)
            return
        await hass.services.async_call("light", "turn_on", dados, blocking=False)
    elif tipo == "numero":
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": entidade, "value": float(params.get("value", 0))},
            blocking=False,
        )


# Convention sent ONLY on voice-panel turns (see is_panel_device). Short on
# purpose: it is paid in tokens on every panel request that reaches Hermes.
PANEL_RULE = (
    "Convenção do painel de voz: se a resposta tiver de mostrar algo no ecrã, "
    'começa com [HW:/display/info:{"text":"..."}] (máx. 60 caracteres, sem repetir '
    "o que dizes em voz alta) e depois o texto normal. O marcador não é falado. "
    'Para o ecrã usa [HW:/light:{"brightness_pct":N}] e para a coluna '
    '[HW:/volume:{"value":N}]: o brilho nunca abaixo de %d e o volume nunca abaixo de %d '
    "(senão não se vê nem se ouve); à noite (das %dh às %dh) o brilho até %d e o volume "
    "até %d; de dia o volume até %d. O que sair disto é corrigido."
    % (
        LIGHT_MIN,
        VOLUME_MIN,
        QUIET_START,
        QUIET_END,
        LIGHT_QUIET_MAX,
        VOLUME_QUIET_MAX,
        DAY_VOLUME_MAX,
    )
)


def is_panel_device(hass, user_input) -> bool:
    """True when the request comes from the MAX35-TV panel (registry: name/model)."""
    satellite = str(getattr(user_input, "satellite_id", "") or "").lower()
    if "mini_tv" in satellite or "max35" in satellite:
        return True
    dev_id = getattr(user_input, "device_id", None)
    if not dev_id:
        return False
    try:
        from homeassistant.helpers import device_registry as dr

        dev = dr.async_get(hass).async_get(dev_id)
    except Exception:  # noqa: BLE001 - registry unavailable must not break the chat
        return False
    if dev is None:
        return False
    campos = " ".join(
        str(x or "") for x in (dev.name, dev.name_by_user, dev.model, dev.manufacturer)
    ).lower()
    return "max35" in campos or "mini tv" in campos
