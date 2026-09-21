# Wake word

The firmware uses `micro_wake_word` running **on the board** (no cloud). The
model configured is **`okay_nabu`** — the one that works best with a pt-PT
accent (tested on the HA app). Push-to-talk is always available and is the
guaranteed fallback if a model misbehaves.

## Which model fires what (measured)

With only `okay_nabu` loaded, measured on the board with the "Last wake word"
sensor:

| Phrase | Result |
|---|---|
| "okay nabu" | fires (best match) |
| "okay hermes" | fires too (close phrase, covered by the same model) |
| "hey nabu" | does not fire |
| "hey hermes" | does not fire |

The two wake phrases in everyday use are both covered by the single
`okay_nabu` model. The `hey_hermes` EN model (miketomkins) was tested and
removed: it ignored the pt-PT accent, occupied tensor arena and had a
permissive cutoff (0.32). Fewer models = fewer false triggers and more arena.

## Sensitivity and false triggers

- `probability_cutoff: 0.93`, tuned from 0.97 (too strict for a pt-PT accent)
  to 0.90 (too loose). At 0.90, with the TV on, the panel woke **by itself**
  and sent TV speech to the agent. 0.93 is the middle.
- The model is trained in English; a non-English accent is the reason it needs
  a lower (more permissive) cutoff in the first place.
- If false triggers return, the right fix is **training a custom model to your
  voice** ([microwakeword.com](https://microwakeword.com)) — not tightening
  the cutoff, which ends up missing real commands.

## Diagnosing a trigger

- The board log is **not persisted**, so look first at the **"Last wake word"**
  `text_sensor` (model + timestamp of each trigger, in HA history). That sensor
  was added precisely because an "invisible" wake-up had no evidence.
- Distinguish wake word from push-to-talk: if `binary_sensor.<board>_button`
  was `off` over the period, the button was not touched → it was a local
  detection.
- The `interval` block logs engine/model state every 60 s (`mwwdiag`); with the
  engine stopped and the model `OFF`, HA externally disabled the models.

## wake word + I2S bus

The wake word engine holds the shared I2S bus while listening. The firmware
stops the engine on `on_start` and restarts it only when the audio has *really*
finished (`on_tts_stream_end`). Never use `on_end` for that (fires tens of
seconds before playback ends → silent speech). See `audio.md`.