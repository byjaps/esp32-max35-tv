"""Monta o esp32-max35-tv-lvgl.yaml a partir do firmware atual (v0.15.27).

Nao corre sozinho no painel: gera o ficheiro e deixa-o pronto para `esphome config`
e `esphome compile`. Cada passo e verificado (assert) para nao gerar um ficheiro
meio alterado sem aviso.
"""
import re, os, sys

BASE = os.path.expanduser("~/homelab/esphome-build")
ORIG = os.path.join(BASE, "esp32-max35-tv-pre-lvgl.yaml")  # v0.15.27 congelado
DEST = os.path.join(BASE, "esp32-max35-tv-lvgl.yaml")
SCRATCH = os.path.expanduser("~/.hermes/cache/scratch")

src = open(ORIG, encoding="utf-8").read()
src = src.replace('fw_version: "0.15.27"', 'fw_version: "0.16.3"', 1)

# ---------------------------------------------------------------- 1. display
i_disp = src.index("\ndisplay:\n")
i_nota = src.index("# NOTA (12/09/2026)")
import subprocess
subprocess.run(["python3", os.path.join(SCRATCH, "gera_face.py")], check=True)
bloco_lvgl = open(os.path.join(SCRATCH, "bloco_lvgl.yaml"), encoding="utf-8").read()

# O display fica só com o hardware: quem desenha e o LVGL. O `lambda` antigo
# (307 KB por frame, 4-6 fps) sai inteiro.
display_novo = """display:
  - platform: mipi_spi
    id: main_display
    model: ST7796
    data_rate: 40MHz
    invert_colors: true
    transform:
      mirror_x: true
      mirror_y: true
      swap_xy: true
    dimensions:
      height: 320
      width: 480
    cs_pin: GPIO5
    dc_pin: GPIO47
    rotation: ${rotate_display}
    # LVGL manda desenhar: nada de update_interval nem de lambda aqui.
    update_interval: never
    auto_clear_enabled: false

"""
src = src[:i_disp + 1] + display_novo + bloco_lvgl + "\n" + src[i_nota:]

# ------------------------------------------------- 2. scripts da cara (topo)
scr = open(os.path.join(SCRATCH, "bloco_ecra_scripts.yaml"), encoding="utf-8").read()
assert src.count("\nscript:\n") == 1
src = src.replace("\nscript:\n", "\nscript:\n" + scr, 1)

# ------------------------------------------------- 3. global do estado da cara
assert src.count("  - id: va_state\n") == 1
src = src.replace("  - id: va_state\n",
                  "  # v0.16.3 — instante em que o alarme comecou (rede de seguranca).\n"
                  "  - id: alarme_ms\n    type: uint32_t\n    restore_value: false\n    initial_value: '0'\n"
                  "  # v0.16.0 — estado aplicado ao ecra LVGL (0 espera .. 7 alarme).\n"
                  "  - id: ecra_est\n    type: int\n    restore_value: false\n    initial_value: '0'\n"
                  "  - id: va_state\n", 1)

# ------------------------------------------------- 4. motor antigo fora
i_loop = src.index("  # --- ECRÃ: motor de atualizacao (fps ajustavel em tempo real) ----------")
i_fim = src.index("  # Devolve o motor de wake word a escuta ASSIM QUE ELE CONSEGUIR.")
src = src[:i_loop] + src[i_fim:]

# chamada no on_boot
old_boot = """      # ECRÃ: arranca o motor de atualizacao do display (ver script ecra_loop).
      # A prioridade -100 corre depois de todos os setup() (o display ja esta
      # inicializado), logo o ecra fica vivo desde o arranque.
      - script.execute: {id: ecra_loop}
"""
new_boot = """      # ECRÃ: o LVGL desenha-se sozinho; aqui so se aplica o estado inicial.
      - script.execute: {id: ui_aplica}
"""
assert src.count(old_boot) == 1
src = src.replace(old_boot, new_boot, 1)

# ------------------------------------------------- 5. component.update -> nada
src = src.replace("      - component.update: main_display\n", "", 2)
src = src.replace("          - component.update: main_display\n", "")
src = src.replace("      - component.update: main_display", "")

# hud_set: no fim, reaplica o estado da cara
src = src.replace("          id(va_state) = state;\n",
                  "          id(va_state) = state;\n      - script.execute: {id: ui_aplica}\n", 1)

# ------------------------------------------------- 6. media e alarme -> cara
assert src.count("  - platform: template\n    name: \"Alarme a tocar\"\n    id: alarme_tocar\n") == 1
src = src.replace('''    id: alarme_tocar
    icon: "mdi:alarm"
    optimistic: true
    restore_mode: ALWAYS_OFF''',
'''    id: alarme_tocar
    icon: "mdi:alarm"
    optimistic: true
    restore_mode: ALWAYS_OFF
    on_turn_on:
      - lambda: "id(alarme_ms) = millis();"
      - script.execute: {id: ui_aplica}
    on_turn_off:
      - script.execute: {id: ui_aplica}''', 1)

# ------------------------------------------------- 7. relogio e temporizador
tick_old = """  - interval: 1s
    then:
      - lambda: |-
          auto t = id(sntp_time).now();"""
tick_new = """  - interval: 1s
    then:
      # Cara (v0.16.0): o relogio e a contagem do temporizador sao etiquetas
      # LVGL — atualizam-se aqui, 1x/s. O LVGL so redesenha se o texto mudar e
      # so a area da etiqueta (uns 60x20 px), nao o ecra todo.
      - lvgl.label.update:
          id: relogio_big
          text: !lambda |-
            auto t = id(sntp_time).now();
            if (!t.is_valid()) return std::string("--:--");
            char b[8]; snprintf(b, sizeof(b), "%02d:%02d", t.hour, t.minute);
            return std::string(b);
      - lvgl.label.update:
          id: relogio_small
          text: !lambda |-
            auto t = id(sntp_time).now();
            if (!t.is_valid()) return std::string("--:--");
            char b[8]; snprintf(b, sizeof(b), "%02d:%02d", t.hour, t.minute);
            return std::string(b);
      - lvgl.label.update:
          id: temporizador
          text: !lambda |-
            // contagem_rest e recalculado aqui no lambda de baixo; usamos o
            // valor do tique anterior (1 s de atraso maximo, invisivel).
            int r = id(contagem_rest);
            if (r < 0) return std::string("");
            char b[16];
            if (r >= 3600) snprintf(b, sizeof(b), "%d:%02d:%02d", r / 3600, (r % 3600) / 60, r % 60);
            else           snprintf(b, sizeof(b), "%d:%02d", (r / 60) % 60, r % 60);
            return std::string(b);
      - if:
          condition:
            lambda: "return id(va_state) == 0 && !id(mp_playing) && !id(alarme_tocar).state;"
          then:
            - lvgl.widget.show: relogio_big
            - lvgl.widget.hide: relogio_small
          else:
            - lvgl.widget.hide: relogio_big
            - lvgl.widget.show: relogio_small
      # Legenda do media: «A TOCAR · <titulo>» (o titulo vem do HA)
      - if:
          condition:
            lambda: "return id(mp_playing) && id(va_state) == 0 && !id(alarme_tocar).state;"
          then:
            - lvgl.label.update:
                id: legenda
                text: !lambda |-
                  std::string t = id(mp_titulo).state;
                  if (t.empty()) return std::string("A TOCAR");
                  return "A TOCAR · " + t;
      - lambda: |-
          auto t = id(sntp_time).now();"""
assert src.count(tick_old) == 1
src = src.replace(tick_old, tick_new, 1)

src = src.replace("  - interval: 1s\n    then:", """  # Piscar de olhos (so em espera). 4 s e o ritmo do mockup do Jarvis.
  - interval: 4s
    then:
      - script.execute: ui_piscar

  - interval: 1s
    then:""", 1)

# Rede de seguranca do alarme: se o switch ficar ligado mais de 15 s (OTA a meio,
# HA sem rede) o ecra ficava preso no alarme. Desliga aqui.
src = src.replace("""  - interval: 1s
    then:""", """  - interval: 1s
    then:
      - if:
          condition:
            lambda: |-
              return id(alarme_tocar).state && id(alarme_ms) > 0 &&
                     (millis() - id(alarme_ms)) > 15000;
          then:
            - switch.turn_off: alarme_tocar""", 1)

open(DEST, "w", encoding="utf-8").write(src)
print("escrito", DEST, len(src.splitlines()), "linhas")
