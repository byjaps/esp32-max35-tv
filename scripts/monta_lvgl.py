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
src = src.replace('fw_version: "0.15.27"', 'fw_version: "0.17.10"', 1)

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
# --- GLIFOS: o "·" do titulo (Artista · Titulo) nao existia nas fontes e saia
# como retangulo vazio no meio do nome da musica. Acrescentados tambem os que
# aparecem em nomes reais de musicas/estacoes.
old_small = '    glyphs: " %°0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÇÉÊÍÓÔÕÚàáâãçéêíóôõú:.,;!?()-_/"'
new_small = '    glyphs: " %°·–&\'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÇÉÊÍÓÔÕÚàáâãçéêíóôõú:.,;!?()-_/"'
assert src.count(old_small) == 2, ("glyphs font_small/normal: esperava 2", src.count(old_small))
src = src.replace(old_small, new_small)
# --- LED da antena: verde a pensar, vermelho quando o pedido esta no agente
old_va = "  on_tts_start:\n"
new_va = """  # LED da antena: verde = a pensar (inclui os intents locais, que nunca chegam
  # ao agente); vermelho = o pedido foi entregue ao agente e estamos a espera.
  on_intent_start:
    - if:
        condition:
          lambda: "return id(ecra_est) == 2;"
        then:
          - lvgl.widget.update: {id: led_antena, bg_color: 0xFF6060}
  on_intent_end:
    - if:
        condition:
          lambda: "return id(ecra_est) == 2;"
        then:
          - lvgl.widget.update: {id: led_antena, bg_color: 0x36E27B}
  on_tts_start:\n"""
assert src.count(old_va) == 1, ("voice_assistant on_tts_start: esperava 1", src.count(old_va))
src = src.replace(old_va, new_va, 1)

src = src.replace("\nscript:\n", "\nscript:\n" + scr, 1)
# Diagnostico: mostrar o estado do ECRA (ecra_est) alem do va_state.
src = src.replace('"rest=%d est=%d mp=%d al=%d ecra=%d fim=%s"',
                  '"rest=%d est=%d mp=%d al=%d ecra=%d ec=%d fim=%s"', 1)
src = src.replace("(int) id(mp_playing), (int) id(alarme_tocar).state, (int) id(ecra_alarme), s.c_str());",
                  "(int) id(mp_playing), (int) id(alarme_tocar).state, (int) id(ecra_alarme), (int) id(ecra_est), s.c_str());", 1)


# ------------------------------------------------- 3. global do estado da cara
assert src.count("  - id: va_state\n") == 1
src = src.replace("  - id: va_state\n",
                  "  # v0.17.0 — trava as cadeias on_stop enquanto se mudam estados.\n"
                  "  - id: anim_ok\n    type: bool\n    restore_value: false\n    initial_value: 'true'\n"
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
# --- ganchos do ecra no media player (v0.17.3) -----------------------------
# Sem isto o ecra nunca entrava em "a tocar": o ui_aplica so corria quando o
# HUD/estado de voz mudava, e a musica ficava em espera sem notas.
# v0.17.4 — o `on_play` do speaker media player nao dispara sempre (o
# `on_turn_on` sim, e e ele que arranca o mp_stop_wake): e ai que se aplica o
# estado do ecra, senao a musica ficava no ecra de espera.
old_sw = '      - lambda: "id(mp_playing) = true; id(mp_armado_ms) = millis();"'
new_sw = ('      - lambda: "id(mp_playing) = true; id(mp_armado_ms) = millis();"\n'
          '      - script.execute: {id: ui_aplica}')
assert src.count(old_sw) == 1, ("mp_stop_wake: ancora nao encontrada", src.count(old_sw))
src = src.replace(old_sw, new_sw, 1)

old_mp = """    on_play:
      - script.execute: {id: mp_stop_wake}
    on_idle:
      - lambda: "id(mp_playing) = false;"
      - script.execute: {id: mp_idle_resume}"""
new_mp = """    on_play:
      - script.execute: {id: mp_stop_wake}
      - script.execute: {id: ui_aplica}
    on_idle:
      - lambda: "id(mp_playing) = false;"
      - script.execute: {id: mp_idle_resume}
      - script.execute: {id: ui_aplica}"""
assert src.count(old_mp) == 1, ("ganchos do media: ancora nao encontrada", src.count(old_mp))
src = src.replace(old_mp, new_mp, 1)


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
      # Relogio: SEMPRE o tamanho grande (pedido do Joel, 29/10). O `relogio_small`
      # fica escondido para sempre; a troca de fonte por estado saiu.
      - lvgl.widget.show: relogio_big
      - lvgl.widget.hide: relogio_small
      # Legenda do media: «A TOCAR · <titulo>» (o titulo vem do HA)
      - if:
          condition:
            lambda: "return id(mp_playing) && id(va_state) == 0 && !id(alarme_tocar).state;"
          then:
            - lvgl.label.update:
                id: legenda
                text: !lambda |-
                  std::string t = id(mp_titulo).state;
                  // Nome da rádio/faixa, a rolar no peito (long_mode:
                  // SCROLL_CIRCULAR). Sem título, fica "A TOCAR".
                  if (t.empty()) return std::string("A TOCAR");
                  return t;
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
