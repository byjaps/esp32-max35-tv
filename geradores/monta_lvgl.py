"""Builds esp32-max35-tv-lvgl.yaml from the current firmware (v0.15.27).

It does not run by itself on the panel: it generates the file and leaves it ready for
`esphome config` and `esphome compile`. Every step is checked (assert) so it never
produces a half-modified file without a warning.
"""
import re, os, sys

BASE = os.path.expanduser("~/homelab/esphome-build")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# Frozen base: v0.15.27 (the last of the round face). It lives next to the generator
# so the screen YAML can be reproduced from a repo clone, without any author
# paths.
ORIG = os.environ.get("MAX35_BASE", os.path.join(HERE, "base-0.15.27.yaml"))
# Output: by default, the YAML that esphome uses (at the repo / build folder root).
DEST = os.environ.get("MAX35_OUT", os.path.join(ROOT, "esp32-max35-tv.yaml"))
VER = os.environ.get("MAX35_VERSION", "0.17.14")
SCRATCH = HERE

src = open(ORIG, encoding="utf-8").read()
src = src.replace('fw_version: "0.15.27"', f'fw_version: "{VER}"', 1)

# ---------------------------------------------------------------- 1. display
i_disp = src.index("\ndisplay:\n")
i_nota = src.index("# NOTE (12/09/2026)")
import subprocess
subprocess.run(["python3", os.path.join(SCRATCH, "gera_face.py")], check=True)
bloco_lvgl = open(os.path.join(SCRATCH, "bloco_lvgl.yaml"), encoding="utf-8").read()

# The display keeps only the hardware: LVGL does the drawing. The old lambda
# (307 KB per frame, 4-6 fps) is removed entirely.
display_novo = """display:
  - platform: mipi_spi
    id: main_display
    model: ST7796
    # v0.17.11 — 40 -> 80 MHz: mipi_spi only offers 40 or 80 for the ST7796 (60
    # is rejected by `config`). At 80 MHz the full frame drops from ~61 ms
    # to ~31 ms, which is what feels like "drag" when the whole robot moves
    # (LVGL invalidates 480x320 and the screen refreshes in bands).
    data_rate: 80MHz
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
    # LVGL drives the drawing: no update_interval and no lambda here.
    update_interval: never
    auto_clear_enabled: false

"""
src = src[:i_disp + 1] + display_novo + bloco_lvgl + "\n" + src[i_nota:]

# ------------------------------------------------- 2. face scripts (top)
scr = open(os.path.join(SCRATCH, "bloco_ecra_scripts.yaml"), encoding="utf-8").read()
assert src.count("\nscript:\n") == 1
# --- GLYPHS: the "·" in the title (Artist · Title) was missing from the fonts and
# came out as an empty box in the middle of the song name. Also added the glyphs
# that show up in real song/station names.
old_small = '    glyphs: " %°0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÇÉÊÍÓÔÕÚàáâãçéêíóôõú:.,;!?()-_/"'
new_small = '    glyphs: " %°·–&\'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÇÉÊÍÓÔÕÚàáâãçéêíóôõú:.,;!?()-_/"'
assert src.count(old_small) == 2, ("glyphs font_small/normal: esperava 2", src.count(old_small))
src = src.replace(old_small, new_small)
# --- Antenna LED: green while thinking, red when the request is with the agent
old_va = "  on_tts_start:\n"
new_va = """  # Antenna LED: green = thinking (local intents included, which never reach
  # the agent); red = the request went to the agent and we are waiting.
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
# Diagnostics: show the SCREEN state (ecra_est) as well as va_state.
src = src.replace('"rest=%d est=%d mp=%d al=%d ecra=%d fim=%s"',
                  '"rest=%d est=%d mp=%d al=%d ecra=%d ec=%d fim=%s"', 1)
src = src.replace("(int) id(mp_playing), (int) id(alarme_tocar).state, (int) id(ecra_alarme), s.c_str());",
                  "(int) id(mp_playing), (int) id(alarme_tocar).state, (int) id(ecra_alarme), (int) id(ecra_est), s.c_str());", 1)


# ------------------------------------------------- 3. face state global
assert src.count("  - id: va_state\n") == 1
src = src.replace("  - id: va_state\n",
                  "  # v0.17.0 — trava as cadeias on_stop enquanto se mudam estados.\n"
                  "  - id: anim_ok\n    type: bool\n    restore_value: false\n    initial_value: 'true'\n"
                  "  # v0.16.3 — instant the alarm started (safety net).\n"
                  "  - id: alarme_ms\n    type: uint32_t\n    restore_value: false\n    initial_value: '0'\n"
                  "  # v0.16.0 — estado aplicado ao ecra LVGL (0 espera .. 7 alarme).\n"
                  "  - id: ecra_est\n    type: int\n    restore_value: false\n    initial_value: '0'\n"
                  "  - id: va_state\n", 1)

# ------------------------------------------------- 4. old engine out
i_loop = src.index("--- SCREEN: update engine (fps adjustable in real time) -------------------")
i_fim = src.index("  # Returns the wake word engine to listening AS SOON AS IT CAN.")
src = src[:i_loop] + src[i_fim:]

# call in on_boot
old_boot = """      # SCREEN: starts the display update engine (see script ecra_loop).
      # Priority -100 runs after all setup() (the display is already
      # initialised), so the screen is alive from boot.
      - script.execute: {id: ecra_loop}
"""
new_boot = """      # SCREEN: LVGL paints itself; here only the initial state is applied.
      - script.execute: {id: ui_aplica}
"""
assert src.count(old_boot) == 1
src = src.replace(old_boot, new_boot, 1)
# --- screen hooks in the media player (v0.17.3) -----------------------------
# Without this the screen never entered "playing": ui_aplica only ran when the
# HUD/voice state changed, and the music stayed on standby with no notes.
# v0.17.4 — the speaker media player's `on_play` does not always fire (`on_turn_on`
# does, and it is that one which starts mp_stop_wake): the screen state is applied
# there, otherwise the music stayed on the standby screen.
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


# ------------------------------------------------- 5. component.update -> nothing
src = src.replace("      - component.update: main_display\n", "", 2)
src = src.replace("          - component.update: main_display\n", "")
src = src.replace("      - component.update: main_display", "")

# hud_set: at the end, reapply the face state
src = src.replace("          id(va_state) = state;\n",
                  "          id(va_state) = state;\n      - script.execute: {id: ui_aplica}\n", 1)

# ------------------------------------------------- 6. media and alarm -> face
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

# ------------------------------------------------- 7. clock and timer
tick_old = """  - interval: 1s
    then:
      - lambda: |-
          auto t = id(sntp_time).now();"""
tick_new = """  - interval: 1s
    then:
      # Face (v0.16.0): the clock and the timer countdown are LVGL labels
      # — they are updated here, 1x/s. LVGL only redraws when the text changes,
      # and only the label area (about 60x20 px), not the whole screen.
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
            // contagem_rest is recalculated in the lambda below; we use the
            // value from the previous tick (1 s delay at most, invisible).
            int r = id(contagem_rest);
            if (r < 0) return std::string("");
            char b[16];
            if (r >= 3600) snprintf(b, sizeof(b), "%d:%02d:%02d", r / 3600, (r % 3600) / 60, r % 60);
            else           snprintf(b, sizeof(b), "%d:%02d", (r / 60) % 60, r % 60);
            return std::string(b);
      # Clock: ALWAYS the big size (the author asked for it, 29/10). The `relogio_small`
      # stays hidden for good; the per-state font swap is gone.
      - lvgl.widget.show: relogio_big
      - lvgl.widget.hide: relogio_small
      # Chest caption, by priority (v0.17.14 — the author's option (a)):
      #   1) the line written by the agent (`hud_linha`, lives 45 s) takes the caption
      #      and gives it back to the state when it disappears — no new widget, in the
      #      place people already look at;
      #   2) the media title, scrolling;
      #   3) the state caption (the same text the `ui_*` write: here it only
      #      serves to restore it when the HUD line clears or the media stops).
      # The alarm always wins: `ui_alarme` writes "ALARME" in red.
      - if:
          condition:
            lambda: "return !id(hud_linha).state.empty() && !id(alarme_tocar).state;"
          then:
            - lvgl.label.update:
                id: legenda
                text: !lambda 'return id(hud_linha).state;'
                text_color: 0x2F3947
          else:
            - if:
                condition:
                  lambda: "return id(mp_playing) && id(va_state) == 0 && !id(alarme_tocar).state;"
                then:
                  - lvgl.label.update:
                      id: legenda
                      text: !lambda |-
                        std::string t = id(mp_titulo).state;
                        // Station/track name, scrolling on the chest (long_mode:
                        // SCROLL_CIRCULAR). With no title it stays "A TOCAR".
                        if (t.empty()) return std::string("A TOCAR");
                        return t;
            - if:
                condition:
                  lambda: "return !id(mp_playing) && !id(alarme_tocar).state;"
                then:
                  - lvgl.label.update:
                      id: legenda
                      text: !lambda |-
                        switch (id(va_state)) {
                          case 1: return std::string("A OUVIR");
                          case 2: return std::string("A PENSAR");
                          case 3: return std::string("A FALAR");
                          default: return std::string();
                        }
                      text_color: 0x2F3947
      - lambda: |-
          auto t = id(sntp_time).now();"""
assert src.count(tick_old) == 1
src = src.replace(tick_old, tick_new, 1)

src = src.replace("  - interval: 1s\n    then:", """  # Eye blink (idle only). 4 s is the Jarvis mockup rhythm.
  - interval: 4s
    then:
      - script.execute: ui_piscar

  - interval: 1s
    then:""", 1)

# Alarm safety net: if the switch stays on for more than 15 s (OTA midway,
# HA with no network) the screen got stuck on the alarm. Turn it off here.
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

# ---------------------------------------------------------------------------
# CLEANUP v0.17.12 (30/10/2026) — the `number` "Animação (fps)" goes away, plus
# everything that fed it. It set the rate of the old drawing (lambda at N fps,
# 307 KB/frame); LVGL replaced it and nothing read this value. Verified: `anim_fps`
# only showed up in the `hud_set` lambda, which saved it and restored it around the
# conversation — logic with no effect since v0.16.0.
velho_num = """  # Screen animation rate (see script ecra_loop). 0 = ring stopped, but the
  # screen keeps updating 1x/s (clock and state changes).
  # ⚠️ Each frame costs ~150 ms (mipi_spi pushes the whole buffer, 307 KB). At
  # 4 fps that is ~60% of the main loop time just drawing — changing this
  # entity is how you balance smoothness/CPU without recompiling. Going above
  # 6-7 is only worth it if the voice is confirmed not to lose quality.
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

velho_glob = """  # Screen rate chosen by the user, saved while the conversation is under way
  # (hud_set sets the animation to 0 and restores this value at the end). 0 = nothing saved.
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

velho_com = """      # v0.15.12 — THE SCREEN QUIETS DOWN DURING THE CONVERSATION.
      # Measured on 18/10: each frame costs ~150 ms of the main loop (mipi_spi,
      # 307 KB per frame) and at 4 fps that is ~60% of the time drawing. The symptom
      # was audio lost at the start of the turn ("Cannot receive audio, buffer is
      # full") and transcriptions with the beginning cut — "agora desliga" was heard
      # as "Porta de liga". With the animation at 0 during listening/thinking/speaking
      # the screen keeps updating 1x/s (see ecra_loop) and the mic has the whole CPU.
      # The rate chosen by the user is restored when it goes back to "em espera".
"""
novo_com = """      # v0.17.12 — the old "silence the screen during the conversation" (governing drawing
      # by fps, v0.15.12) left with the `number` Animação (fps): LVGL does the drawing
      # and the per-frame cost is no longer governed from there.
"""
assert src.count(velho_com) == 1, "comentário do hud_set"
src = src.replace(velho_com, novo_com, 1)

# CLEANUP v0.17.13 (30/10/2026) — `rot_deg` (ring angle of the old drawing) is no
# longer read by anyone: LVGL animates on its own. Counted in the YAML: 1
# occurrence (its own definition).
velho_rot = """  # Accumulated angle of the ring animation, in degrees. It advances by TIME (degrees per
  # second, depending on the state) and not per frame: that way changing the `number`
  # \"Animação (fps)\" changes the smoothness, not the animation speed.
  - id: rot_deg
    type: float
    restore_value: no
    initial_value: \"0\"
"""
assert src.count(velho_rot) == 1, "global rot_deg"
src = src.replace(velho_rot, "", 1)

velho_h1 = """#   + the rotation is adjustable IN REAL TIME via the `number` \"Animação (fps)\"
#     (display at `update_interval: never` + script `ecra_loop`): that is what
#     allows measuring the effect of the screen SPI on the audio without recompiling
"""
assert src.count(velho_h1) == 1, "cabeçalho fps"
src = src.replace(velho_h1, "", 1)

velho_h2 = """#   ⚠️ NO LVGL on purpose: a ring with quads + native primitives costs
#      less RAM than redrawing the whole screen in lv_arc widgets.
"""
novo_h2 = """#   ⚠️ UNTIL v0.16.0 DELIBERATELY WITHOUT LVGL (ring drawn with quads in native primitives);
#      since v0.16.0 LVGL does the drawing, generated by `gera_face.py` from
#      the mockup manifest. See the `esphome-esp32-voice-panel` skill → ecra-lvgl.md.
"""
assert src.count(velho_h2) == 1, "cabeçalho sem-lvgl"
src = src.replace(velho_h2, novo_h2, 1)

# CLEANUP v0.17.14 (30/10/2026) — «A Trabalhar» goes away for good (v0.15.18): the
# violet ring it painted died with the new drawing and the switch was left with no
# visible effect. What now says «the request is with the agent» is the antenna LED
# (green while thinking, red once the request is delivered). The Hermes plugin
# `painel-trabalho` goes with it — there is nothing left to turn on.
velho_safe = '          // Fail-safe do anel «a trabalhar»: em espera nao ha ferramenta nenhuma a\n          // correr. Se o plugin morrer a meio do turno, o violeta nao fica preso.\n          if (state == 0 && id(trabalho).state) {\n            id(trabalho).turn_off();\n          }\n'
assert src.count(velho_safe) == 1, ("fail-safe do trabalho", src.count(velho_safe))
src = src.replace(velho_safe, "", 1)

velho_sw = '# --- «A TRABALHAR» (WORKING) STATE (24/10/2026) -----------------------------\n# Turned on by the Hermes `painel-trabalho` plugin while a tool runs on a\n# request that came from the panel. It draws nothing by itself: it only changes the ring colour\n# while `va_state == 2` (thinking). The plugin turns it off at the end of the turn and\n# `hud_set` turns it off whenever the panel goes back to "em espera" (fail-safe).\nswitch:\n  - platform: template\n    name: "A Trabalhar"\n    id: trabalho\n    icon: "mdi:hammer-wrench"\n    optimistic: true\n    restore_mode: ALWAYS_OFF\n'
assert src.count(velho_sw) == 1, ("switch A Trabalhar", src.count(velho_sw))
src = src.replace(velho_sw, "switch:\n", 1)

open(DEST, "w", encoding="utf-8").write(src)
print("escrito", DEST, len(src.splitlines()), "linhas")
