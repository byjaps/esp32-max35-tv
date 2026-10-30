"""Insere no monta_lvgl.py a limpeza do `number` Animação (fps) (v0.17.12).

Corre uma vez; idempotente (se o bloco já lá estiver, não duplica).
"""
import os

P = "/home/hermes/.hermes/cache/scratch/monta_lvgl.py"
src = open(P, encoding="utf-8").read()

if "LIMPEZA v0.17.12" in src:
    print("já aplicado")
    raise SystemExit(0)

BLOCO = r'''
# ---------------------------------------------------------------------------
# LIMPEZA v0.17.12 (30/10/2026) — sai o `number` "Animação (fps)" e tudo o que o
# alimentava. Era o ritmo do desenho antigo (lambda a N fps, 307 KB/frame); o
# LVGL substituiu-o e nada lia este valor. Verificado: `anim_fps` só aparecia no
# lambda do `hud_set`, que o guardava e repunha à volta da conversa — lógica sem
# efeito desde a v0.16.0.
velho_num = """  # Ritmo da animacao do ecra (ver script ecra_loop). 0 = anel parado, mas o
  # ecra continua a atualizar 1x/s (relogio e mudancas de estado).
  # ⚠️ Cada frame custa ~150 ms (o mipi_spi empurra o buffer todo, 307 KB). Em
  # 4 fps sao ~60% do tempo do loop principal so a desenhar — mexer nesta
  # entidade e a forma de equilibrar fluidez/CPU sem recompilar. Subir acima de
  # 6-7 so vale a pena se se confirmar que a voz nao perde qualidade.
  - platform: template
    name: "Animação (fps)"
    id: anim_fps
    icon: "mdi:speedometer"
    entity_category: config
    optimistic: true
    unit_of_measurement: "fps"
    min_value: 0
    max_value: 15
    step: 1
    initial_value: 4
    restore_value: true

"""
assert src.count(velho_num) == 1, "número anim_fps"
src = src.replace(velho_num, "", 1)

velho_glob = """  # Ritmo do ecrã escolhido pelo utilizador, guardado enquanto a conversa decorre
  # (hud_set põe a animação a 0 e repõe este valor no fim). 0 = nada guardado.
  - id: fps_user
    type: float
    restore_value: no
    initial_value: "0"
"""
assert src.count(velho_glob) == 1, "global fps_user"
src = src.replace(velho_glob, "", 1)

velho_lambda = """          auto *num = id(anim_fps);
          if (state != 0) {
            if (num->state > 0.0f && id(fps_user) <= 0.0f) {
              id(fps_user) = num->state;
              num->make_call().set_value(0.0f).perform();
            }
          } else if (id(fps_user) > 0.0f) {
            num->make_call().set_value(id(fps_user)).perform();
            id(fps_user) = 0.0f;
          }
"""
assert src.count(velho_lambda) == 1, "lambda do hud_set"
src = src.replace(velho_lambda, "", 1)

velho_com = """      # v0.15.12 — O ECRÃ CALA-SE DURANTE A CONVERSA.
      # Medido a 18/10: cada frame custa ~150 ms de loop principal (mipi_spi,
      # 307 KB por frame) e a 4 fps isso é ~60% do tempo a desenhar. O sintoma
      # era áudio perdido no arranque do turno ("Cannot receive audio, buffer is
      # full") e transcrições com o início cortado — "agora desliga" foi ouvido
      # como "Porta de liga". Com a animação a 0 durante a escuta/pensamento/fala
      # o ecrã continua a atualizar 1x/s (ver ecra_loop) e o micro tem o CPU todo.
      # O ritmo escolhido pelo utilizador é reposto quando volta a "em espera".
"""
novo_com = """      # v0.17.12 — o antigo "cala o ecrã durante a conversa" (governar o desenho
      # por fps, v0.15.12) saiu com o `number` Animação (fps): quem desenha é o
      # LVGL e o custo por frame já não se governa por ali.
"""
assert src.count(velho_com) == 1, "comentário do hud_set"
src = src.replace(velho_com, novo_com, 1)
'''

alvo = '\nopen(DEST, "w", encoding="utf-8").write(src)'
assert src.count(alvo) == 1
src = src.replace(alvo, BLOCO + alvo, 1)
open(P, "w", encoding="utf-8").write(src)
print("bloco de limpeza inserido em monta_lvgl.py")
