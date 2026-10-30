# The screen — a robot face in LVGL

Since **v0.16.0** the panel draws a robot face with **LVGL** instead of the ring
HUD rendered by a `display:` lambda. The last build of the old series is
**v0.15.27** (tag `v0.15.27`): if you prefer that look, compile from that tag.

## Why LVGL

The lambda path could not animate. A full 480×320 frame at 16 bpp is **307 KB**,
and on this board the `mipi_spi` driver takes **~150 ms** to push it — a hard
ceiling of 4-6 fps. That is fine for a clock and a slow ring; a face that blinks,
looks around and shakes in an alarm reads as broken at 5 fps.

LVGL invalidates only the widgets that changed and redraws those areas. The
display runs at **80 MHz** (the ST7796 accepts 40 or 80 MHz — `60MHz` is rejected
by `esphome config`), which brings a full-screen redraw from ~61 ms to ~31 ms.
Everything below is a consequence of those two numbers.

## States

One global, `ecra_est` (0-7), drives the whole screen. It is **not** `va_state` —
the voice state stays what it was; the screen state is derived in `ui_aplica`
(alarm beats everything, media only outside a conversation).

| `ecra_est` | When | Face | Caption |
|---|---|---|---|
| 0 | idle | eyes open + smile, blinks every 4 s | — (big clock) |
| 1 | listening | eyebrows up, three sound waves, ear LEDs cyan | `A OUVIR` |
| 2 | thinking / request sent | eyes glance up-right, head tilt, three dots, antenna green (red while the request is with the agent) | `A PENSAR` |
| 3 | speaking | mouth alternates open/closed every 160 ms | `A FALAR` |
| 4 | music playing | eyes closed and happy, notes bobbing, title scrolling on the chest | `A TOCAR` |
| 5 | night | dimmed shell, closed eyes, `Z z z` | — |
| 6 | no HA connection | red X eyes, frown, red antenna | `SEM LIGAÇÃO` |
| 7 | timer alarm | eyes 56×56 with halo and highlight, `!` shapes, mouth alternating, rings 14→44 px, slow shake | `ALARME` |

The clock is always the **big** font (a measurement preference: the small font
made the time unreadable from the sofa). During music the track/station name
scrolls in a label with `long_mode: SCROLL_CIRCULAR`; where the name comes from is
in [`media-player.md`](media-player.md).

## The timer

Three independent slots (`timer.temporizador_1..3`, created on the HA side) started
by **local intents** in Portuguese — minutes, seconds and hours, digits or words
("temporizador de 10 minutos", "avisa-me daqui a meia hora"). No LLM is involved,
so the answer is immediate and works with the internet down.

What this firmware provides for it:

| Entity | Role |
|---|---|
| `text.<panel>_contagem_do_temporizador_fim` | HA writes the **epoch** when a timer ends; the firmware counts it down itself, so there is no per-second traffic and the display survives a WiFi hiccup. |
| `switch.<panel>_alarme_a_tocar` | Turns the screen into the alarm face (state 7). `ALWAYS_OFF` at boot, plus a 15 s watchdog that turns it off if HA dies mid-alarm. |

The countdown is a red label under the clock (`H:MM:SS` above one hour) and the
alarm face enters **1 s before** the countdown reaches zero, so the white clock
never flashes between the last second and the alarm. The 10 s alarm itself is the
HA side (`script` + automation: raise the volume to the safe maximum, play a local
WAV, restore the previous volume).

The voice side is not shipped in this repository: it is three intent scripts, three
sentence lists and two automations on the Home Assistant side, wired to those
entities. Publish them in your own `intent_scripts.yaml` / `custom_sentences/` /
`automations.yaml`, or ask the agent to write them from this table.

## Generated, not hand-written

The screen is ~100 widgets with coordinates measured from design mockups — typing
that by hand once is a day, keeping it by hand is a trap. So it is generated:

| File | Role |
|---|---|
| `geradores/gera_face.py` | Geometry (`M`, absolute coordinates inside transparent groups) and every animation; writes `bloco_lvgl.yaml`. |
| `geradores/monta_lvgl.py` | Assembles the final YAML: takes the frozen pre-LVGL base, swaps the `display:` for LVGL, injects the screen scripts, patches the media/alarm hooks. Writes `esp32-max35-tv.yaml`. |
| `geradores/bloco_ecra_scripts.yaml` | The screen scripts (`ui_base`, `ui_pensar`, …) and the timer/alarm glue. |
| `geradores/base-0.15.27.yaml` | Frozen v0.15.27 config the generator starts from. |

```bash
python3 geradores/monta_lvgl.py          # rewrites esp32-max35-tv.yaml
python3 scripts/preview_lvgl.py out/     # renders the 8 states with the SAME coordinates
esphome config esp32-max35-tv.yaml
```

The regenerated YAML is **byte-identical** to the file in this repository — that
is the check that nobody hand-edited it. `preview_lvgl.py` exists because a
compile + OTA is ~10 minutes: look at the render first, then flash.

⚠️ The geometry is a **copy** of numbers measured from the mockups; the generator
does **not** read the design file. Change the design, update `M` by hand.

## What breaks it (all measured on the real panel)

- **`arc` and `line` render grey.** Their colour properties do not win against
  the theme on this build. Draw everything with `obj`: filled ellipses, and a
  second ellipse in the background colour on top for crescents, hollow mouths and
  eyebrows.
- **Every `obj` scrolls by default.** Content larger than its container (the
  chest) draws a scrollbar on the right — easy to mistake for a hardware defect.
  Set `scroll_dir: NONE` and `scrollbar_mode: "OFF"` (quoted: bare `OFF` becomes a
  YAML boolean and the config fails).
- **`width`/`height` are not animatable.** Use `transform_width`/`transform_height`
  (and `transform_scale`); the pivot defaults to the top-left corner, so rotating
  a head needs `transform_pivot_x/y: 50%`.
- **`transform_rotation` is 0-360 and rejects negatives.** Never write `355` to mean
  `-5°`: the value is interpolated and the head spins a full turn.
- **`loop` from X to Y jumps back each cycle.** That is a tremble, not a shake.
  Use `timing: round_trip` + `ease_in_out`; `loop` with `Y≠X` at 90 ms produced
  ~11 jumps per second — faster than the panel can draw.
- **`on_stop` also fires when code stops the animation.** A→B→A chained on
  `on_stop` becomes an endless ping-pong on every state change. Guard it with a
  global that `ui_base` clears before stopping.
- **`start_delay` is applied on every loop**, so it cannot phase-shift animations;
  start them from a script with `delay` between them.
- **The font refuses duplicate glyphs** (`" ALARME"` → `Found duplicate glyph: A`);
  only `esphome config` tells you.
- **`widgets:` is declared once per group**, indentation +4 per level. A stray
  second `widgets:` gives `Unknown widget type: widgets`, buried in the failure
  dump — grep for that instead of reading the whole tree.
- **80 MHz can be too fast for the wiring.** Dotted lines, stripes or swapped
  colours mean going back to `40MHz` — one line, one OTA.

## Verifying what is on the panel

`esphome config` validates the schema; only `esphome compile` catches C++ errors;
and only the device tells you what is running. After an OTA, read
`sensor.<board>_versao_do_firmware` — a "successful" upload that boots the old
version is a rollback. A render on a computer is not the panel: ask for a photo.
