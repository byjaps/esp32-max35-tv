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
from datetime import datetime
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

# ---------------------------------------------------------------------------
# Limites ABAIXO do agente (princípio «a segurança não se pede ao modelo»).
# O prompt já diz ao agente estes números (PANEL_RULE); isto é a última linha de
# defesa, para o caso de ele se esquecer ou de um pedido vir de outro sítio.
# Mudar aqui e na PANEL_RULE — os dois valores têm de contar a mesma história.
# ---------------------------------------------------------------------------
QUIET_START, QUIET_END = 23, 8          # horas locais do HA
QUIET_LIGHT_MAX = 15                    # % de brilho máximo à noite
QUIET_VOLUME_MAX = 35                   # % de volume máximo à noite
DAY_VOLUME_MAX = 80                     # teto de dia (a coluna é pequena)

# (rota, campo) -> (mínimo, máximo de dia, máximo à noite)
LIMITES: dict[tuple[str, str], tuple[float, float, float]] = {
    ("/light", "brightness_pct"): (0, 100, QUIET_LIGHT_MAX),
    ("/volume", "value"): (0, DAY_VOLUME_MAX, QUIET_VOLUME_MAX),
}


def _em_quiet_hours(agora: datetime) -> bool:
    h = agora.hour
    return h >= QUIET_START or h < QUIET_END


def _limitar(
    rota: str, params: dict[str, Any], agora: datetime | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Corta o que passa dos limites. Devolve (params, cortes). Função pura."""
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
            cortes.append(f"{campo} inválido ({dados[campo]!r}) — descartado")
            dados.pop(campo)
            continue
        teto = max_noite if quiet else max_dia
        if valor > teto:
            dados[campo] = int(teto) if float(teto).is_integer() else teto
            cortes.append(f"{campo} {valor:g}->{teto:g} ({'noite' if quiet else 'dia'})")
        elif valor < minimo:
            dados[campo] = minimo
            cortes.append(f"{campo} {valor:g}->{minimo:g} (mínimo)")
    return dados, cortes


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


_rotas_verificadas = False


def validar_rotas(hass) -> list[str]:
    """Confirma que as entidades de ROTAS existem. Uma vez por processo.

    Sem isto, um firmware novo que renomeie uma entidade deixa o marcador a morrer
    em silêncio (aconteceu a 23/10 com `text.mini_tv_linha_hud`). Não corrige nada:
    diz o que falta, para se corrigir a tabela.
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
                "HW rotas: a entidade %s (%s) não existe — os marcadores dessa rota "
                "são descartados até a tabela ROTAS ser corrigida",
                entidade,
                rota,
            )
    if not faltam:
        _LOGGER.debug("HW rotas: %d rotas verificadas, todas presentes", len(ROTAS))
    return faltam


async def fire_hw_calls(hass, chamadas: list[tuple[str, dict[str, Any]]]) -> None:
    """Dispara as acções. Fire-and-forget: falha de hardware nunca estraga a fala."""
    validar_rotas(hass)
    for rota, params in chamadas:
        destino = ROTAS.get(rota)
        if destino is None:
            _LOGGER.debug("HW marcador sem rota mapeada: %s", rota)
            continue
        entidade, tipo = destino
        if hass.states.get(entidade) is None:
            _LOGGER.warning("HW marcador %s: a entidade %s não existe", rota, entidade)
            continue
        params, cortes = _limitar(rota, params)
        for corte in cortes:
            _LOGGER.info("HW limite aplicado em %s: %s", rota, corte)
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
    "o que dizes em voz alta) e depois o texto normal. O marcador não é falado. "
    "Para o ecrã usa [HW:/light:{\"brightness_pct\":N}] e para a coluna "
    "[HW:/volume:{\"value\":N}]: brilho no máximo 15 e volume no máximo 35 entre as "
    f"{QUIET_START}h e as {QUIET_END}h; de dia o volume não passa de {DAY_VOLUME_MAX}. "
    "Valores acima disso são cortados."
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
