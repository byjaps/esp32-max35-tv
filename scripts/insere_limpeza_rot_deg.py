"""v0.17.13: tira o global `rot_deg` (morto desde o LVGL) e comentários de cabeçalho
que descrevem o desenho antigo (fps / ecra_loop / «sem LVGL»)."""
P = "/home/hermes/.hermes/cache/scratch/monta_lvgl.py"
src = open(P, encoding="utf-8").read()

if "LIMPEZA v0.17.13" in src:
    print("já aplicado")
    raise SystemExit(0)

BLOCO = r'''
# LIMPEZA v0.17.13 (30/10/2026) — `rot_deg` (ângulo do anel do desenho antigo) já
# não é lido por ninguém: o LVGL anima sozinho. Contado no YAML: 1 ocorrência
# (a própria definição).
velho_rot = """  # Angulo acumulado da animacao do anel, em graus. Avanca por TEMPO (graus por
  # segundo, conforme o estado) e nao por frame: assim mexer no `number`
  # \"Animação (fps)\" muda a fluidez, nao a velocidade da animacao.
  - id: rot_deg
    type: float
    restore_value: no
    initial_value: \"0\"
"""
assert src.count(velho_rot) == 1, "global rot_deg"
src = src.replace(velho_rot, "", 1)

velho_h1 = """#   + a rotacao e ajustavel EM TEMPO REAL pelo `number` \"Animação (fps)\"
#     (display em `update_interval: never` + script `ecra_loop`): e o que
#     permite medir o efeito do SPI da tela no audio sem recompilar
"""
assert src.count(velho_h1) == 1, "cabeçalho fps"
src = src.replace(velho_h1, "", 1)

velho_h2 = """#   ⚠️ SEM LVGL de proposito: um anel com quads + primitivas nativas custa
#      menos RAM do que reescrever o ecra todo em widgets lv_arc.
"""
novo_h2 = """#   ⚠️ ATÉ v0.16.0 SEM LVGL de proposito (anel com quads em primitivas nativas);
#      desde a v0.16.0 quem desenha é o LVGL, gerado por `gera_face.py` a partir
#      do manifest do mockup. Ver a skill `esphome-esp32-voice-panel` → ecra-lvgl.md.
"""
assert src.count(velho_h2) == 1, "cabeçalho sem-lvgl"
src = src.replace(velho_h2, novo_h2, 1)
'''

alvo = '\nopen(DEST, "w", encoding="utf-8").write(src)'
assert src.count(alvo) == 1
open(P, "w", encoding="utf-8").write(src.replace(alvo, BLOCO + alvo, 1))
print("bloco v0.17.13 inserido")
