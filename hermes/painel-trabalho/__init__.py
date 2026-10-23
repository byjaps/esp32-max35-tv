"""Anel «a trabalhar» no painel de voz (MAX35-TV).

Enquanto uma ferramenta corre num pedido que veio do painel, o anel fica **violeta** em vez
do âmbar do «a pensar». Quem sabe que uma ferramenta está a correr é o Hermes, não o HA —
por isso este plugin usa o hook oficial `pre_tool_call`.

Regras de desenho (aprendidas à força):
- **Só na sessão da voz** (`ha-voice`): no Telegram uma tool dura minutos e o anel ficaria
  violeta sem sentido.
- **Nunca bloqueia**: tudo em thread, `timeout=2`, qualquer erro é engolido (fail-open).
  O hook está no caminho de TODAS as chamadas — um bug aqui não pode travar trabalho.
- **Sem contadores partidos**: liga na tool e desliga sozinho 3,5 s depois da última (o
  `post_tool_call` não recebe o `session_id`, logo não serve para fechar o turno). O firmware
  tem o fail-safe: ao voltar a «em espera» desliga o switch.
- **Entidade descoberta, não inventada**: procura o `switch.*_a_trabalhar` no HA e guarda o
  id. Se um dia o firmware renomear a entidade, volta a descobrir em vez de falhar em silêncio.
"""
from __future__ import annotations

import logging
import os
import threading
import time

_LOG = logging.getLogger(__name__)

SESSAO_VOZ = "ha-voice"
SEGUNDOS_FIM = 3.5          # tempo que o anel fica violeta depois da última ferramenta
_SUFIXO = "_a_trabalhar"

_env: dict[str, str] = {}
_entidade: str | None = None
_lock = threading.Lock()
_timer: threading.Timer | None = None


def _cfg() -> dict[str, str]:
    """Lê HASS_URL/HASS_TOKEN do .env canónico (uma vez)."""
    global _env
    if _env:
        return _env
    caminho = os.path.expanduser("~/.hermes/.env")
    valores: dict[str, str] = {}
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                k, v = linha.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    _env = {
        "url": (valores.get("HASS_URL") or "http://192.168.31.180:8123").rstrip("/"),
        "token": valores.get("HASS_TOKEN") or os.environ.get("HASS_TOKEN", ""),
    }
    return _env


def _pedido(metodo: str, caminho: str, corpo: dict | None = None) -> dict | None:
    import json
    import urllib.request

    cfg = _cfg()
    if not cfg["token"]:
        return None
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(
        cfg["url"] + caminho,
        data=dados,
        method=metodo,
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=2) as r:  # noqa: S310 - URL própria do homelab
        return json.loads(r.read() or b"{}")


def _descobrir() -> str | None:
    """O entity_id do switch do painel (sem depender de um nome exato)."""
    global _entidade
    if _entidade:
        return _entidade
    try:
        estados = _pedido("GET", "/api/states") or []
    except Exception:  # noqa: BLE001
        return None
    candidatos = [
        e["entity_id"]
        for e in estados
        if isinstance(e, dict)
        and str(e.get("entity_id", "")).startswith("switch.")
        and str(e.get("entity_id", "")).endswith(_SUFIXO)
    ]
    if len(candidatos) == 1:
        _entidade = candidatos[0]
        _LOG.info("painel-trabalho: entidade %s", _entidade)
    elif len(candidatos) > 1:
        _LOG.warning("painel-trabalho: %d switches terminados em %s — sem escolha", len(candidatos), _SUFIXO)
    return _entidade


def _ligar(valor: bool) -> None:
    global _entidade
    for _tentativa in (0, 1):  # 2.ª volta: redescoberta se a entidade mudou
        entidade = _descobrir()
        if not entidade:
            return
        servico = "turn_on" if valor else "turn_off"
        try:
            _pedido("POST", f"/api/services/switch/{servico}", {"entity_id": entidade})
            return
        except Exception as exc:  # noqa: BLE001
            _entidade = None
            if _tentativa:
                _LOG.debug("painel-trabalho: falhou %s (%s)", servico, exc)


def _agendar_desligar() -> None:
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(SEGUNDOS_FIM, lambda: _ligar(False))
        _timer.daemon = True
        _timer.start()


def on_pre_tool_call(tool_name: str = "", args=None, session_id: str = "", **_: object):
    """Hook `pre_tool_call`: liga o anel só nos pedidos que vêm do painel."""
    try:
        if SESSAO_VOZ not in (session_id or ""):
            return None
        # set_value é usado pelo próprio plugin; ignorar não é preciso, mas
        # ferramentas do painel nunca chamam isto.
        threading.Thread(target=_ligar, args=(True,), daemon=True).start()
        _agendar_desligar()
    except Exception:  # noqa: BLE001 - fail-open absoluto
        pass
    return None


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
