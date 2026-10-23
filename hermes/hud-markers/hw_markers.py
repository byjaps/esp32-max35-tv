"""Marcadores [HW:...] na resposta do agente -> acções em dispositivos.

Convenção (padrão lampOS, adaptada): o agente escreve, tipicamente no início da
resposta,

    [HW:/display/info:{"text":"14:30"}]
    [HW:/light:{"brightness_pct":40}]
    [HW:/volume:{"value":30}]

O marcador NÃO é falado: é extraído, traduzido para um serviço do HA e removido
do texto antes de chegar ao TTS. Custa zero voltas de inferência.

Regra do ensaio de 23/10/2026: **limpar primeiro, executar só o que faz parse.**
O regex estrito do upstream não apanha JSON com objeto aninhado; um marcador não
apanhado era falado em voz alta. Aqui o texto é limpo com o regex largo e só os
marcadores que passam `json.loads` são executados.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Forma canónica: [HW:/rota/sub:{"json"}] — corpo opcional.
_HW_STRICT = re.compile(r"\[HW:((?:/[^{:\]]+(?::[^{:\]]+)*))(?::(\{[^}]*\}))?\]")
# Variante link markdown: [Luzes off!](HW:/led/off:{}) -> marcador + label.
_HW_LINK = re.compile(
    r"\[([^\]]*)\]\(\s*HW:\s*((?:/[^(){:\s]+(?::[^(){:\s]+)*))(?::(\{[^}]*\}))?:?\s*\)",
    re.I,
)
# Rede de limpeza: apaga QUALQUER coisa com forma de marcador, mesmo inválida.
_HW_LOOSE = re.compile(r"\[HW:[^\]]*\]")

# Texto de recurso quando a resposta era SÓ marcadores (senão o TTS fica mudo).
SPEECH_FALLBACK = "Feito."

# Rotas suportadas. O entidade tem de existir no HA; se não existir, o marcador
# é descartado com um aviso — nunca se inventa um destino.
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
    """Devolve (chamadas válidas, texto limpo de marcadores)."""
    if not texto or "[HW:" not in texto and "](HW:" not in texto:
        return [], texto

    texto = _normalizar_links(texto)
    chamadas: list[tuple[str, dict[str, Any]]] = []
    for m in _HW_STRICT.finditer(texto):
        rota = "/" + m.group(1).lstrip("/").replace(":", "/")
        corpo = m.group(2) or "{}"
        try:
            params = json.loads(corpo)
        except Exception:  # noqa: BLE001 - marcador inválido: apaga-se, não se executa
            _LOGGER.warning("HW marcador com JSON inválido em %s: %r", rota, corpo[:120])
            continue
        if not isinstance(params, dict):
            continue
        chamadas.append((rota, params))

    limpo = _HW_LOOSE.sub("", texto)
    limpo = re.sub(r"[ \t]{2,}", " ", limpo)
    limpo = re.sub(r"\n{3,}", "\n\n", limpo).strip()
    return chamadas, limpo


async def fire_hw_calls(hass, chamadas: list[tuple[str, dict[str, Any]]]) -> None:
    """Dispara as acções. Fire-and-forget: falha de hardware nunca estraga a fala."""
    for rota, params in chamadas:
        destino = ROTAS.get(rota)
        if destino is None:
            _LOGGER.debug("HW marcador sem rota mapeada: %s", rota)
            continue
        entidade, tipo = destino
        if hass.states.get(entidade) is None:
            _LOGGER.warning("HW marcador %s: a entidade %s não existe", rota, entidade)
            continue
        try:
            await _chamar(hass, entidade, tipo, params)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("HW marcador %s falhou em %s: %s", rota, entidade, exc)


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


# Convenção enviada SÓ nos turnos do painel de voz (ver is_panel_device). Curta
# de propósito: é paga em tokens a cada pedido do painel que chega ao Hermes.
PANEL_RULE = (
    "Convenção do painel de voz: se a resposta tiver de mostrar algo no ecrã, "
    'começa com [HW:/display/info:{"text":"..."}] (máx. 60 caracteres, sem repetir '
    "o que dizes em voz alta) e depois o texto normal. O marcador não é falado."
)


def is_panel_device(hass, user_input) -> bool:
    """True quando o pedido vem do painel MAX35-TV (registry: nome/modelo)."""
    satellite = str(getattr(user_input, "satellite_id", "") or "").lower()
    if "mini_tv" in satellite or "max35" in satellite:
        return True
    dev_id = getattr(user_input, "device_id", None)
    if not dev_id:
        return False
    try:
        from homeassistant.helpers import device_registry as dr

        dev = dr.async_get(hass).async_get(dev_id)
    except Exception:  # noqa: BLE001 - registry indisponível não pode partir a conversa
        return False
    if dev is None:
        return False
    campos = " ".join(
        str(x or "") for x in (dev.name, dev.name_by_user, dev.model, dev.manufacturer)
    ).lower()
    return "max35" in campos or "mini tv" in campos
