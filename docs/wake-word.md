# Wake word

The firmware runs `micro_wake_word` **on the board** (no cloud, no subscription).
**Two models run side by side** — and between them the panel wakes on **four
phrasings** in everyday use (the two models hear each other's phrase, and the
wrong-accent problem disappears when one of them was trained in your own
language):

| Model (`models:` entry) | Phrase | Language | Cutoff | Role |
|---|---|---|---|---|
| `okay_nabu` | "okay nabu" | EN (official ESPHome model) | `0.93` | the stock phrase; permissive cutoff needed for a non-English accent |
| `ok_hermes.json` | "ok hermes" | PT (custom-trained) | `0.5` | dedicated phrase, trained in Portuguese — fires reliably at a far lower cutoff |

Push-to-talk (BOOT button, ≥600 ms) is always available and is the guaranteed
fallback if a model misbehaves.

## What fires what (measured on the board)

Evidence comes from the **"Last wake word"** `text_sensor` (model name +
timestamp of every trigger, kept in HA history — the board log is not persisted):

| Phrase said | Model recorded |
|---|---|
| "okay nabu" | `Okay Nabu` |
| "ok hermes" | `ok hermes` |
| "okay hermes" | either of the two — the phrases overlap, and both models hear it |
| "hey hermes" / "hey nabu" | works with both models loaded (it did **not** with `okay_nabu` alone — see the note below) |

Both models were confirmed firing in real use over a full evening of testing
(dozens of triggers, alternating between the two). The overlapping phrase is why
the sensor sometimes names one model and sometimes the other for what sounds
like the same words: it is not a fault.

> **History, because it explains the design:** with a single `okay_nabu` model the
> English word pair `hey nabu` / `hey hermes` never fired, and the `hey_hermes`
> model from `miketomkins` was tested and dropped (it ignored the pt-PT accent).
> Adding a model **trained in Portuguese** — instead of tightening or loosening
> the English one — is what made the extra phrasings work.

## Adding another wake word

Source of models: the **Wake Word Library — [microwakeword.com/library](https://microwakeword.com/library)**
(free community library of microWakeWord models, and the training service that
produced `ok_hermes`). Related, also useful:

- [esphome/micro-wake-word-models](https://github.com/esphome/micro-wake-word-models) — the official models ESPHome ships (`okay_nabu`, `hey_jarvis`, …).
- [kahrendt/microWakeWord](https://github.com/kahrendt/microWakeWord) — the engine itself (training your own).
- [openwakeword.com/library](https://openwakeword.com/library) — sister library, but those models are for **servers/add-ons** (ONNX), *not* for this board.

To add one:

1. Get the model's **manifest `.json` + `.tflite`** (the library/training service
   hands both out). Drop them in `models/` next to the existing one.
   Only **microWakeWord v2 TFLite INT8** models run here — verify the signature:
   INT8 input `[1,3,40]`, output `[1,1]`. `.pmdl`, `.onnx` and ESP-SR models are
   a different family and will not load.
2. Add a block to `micro_wake_word:` → `models:` with `model: <name>.json`, an
   `id:` and a `probability_cutoff:` (start around `0.5` for a pt-trained model,
   `0.9`+ for an English model used with a pt accent).
3. **Enable it explicitly — read the next section, this is the step that bites.**

## ⚠️ A second model boots DISABLED

ESPHome's codegen sets `default_enabled` only for the **first** entry of
`models:` (`default_enabled = i == 0`). Every other model is left disabled on
boot, **silently**: no error, no warning, the new phrase simply never fires.

The config therefore calls `micro_wake_word.enable_model` for each model
explicitly, and the 60 s diagnostic interval (`mwwdiag`) re-checks and re-enables
them. If you add a model and it never fires, this is the first thing to look at —
the interval log prints the state of each model.

## ⚠️ Home Assistant can disable them all

`VoiceAssistant::on_set_configuration()` disables **every** model and re-enables
only the ones HA sends it in the `active_wake_words` list. If the wake-word
selects in HA show `no_wake_word` (an empty list), every model ends up off. The
`mwwdiag` interval log tells you which of the two situations you are in.

## Sensitivity and false triggers

- `okay_nabu` runs at `probability_cutoff: 0.93`, tuned from 0.97 (too strict for
  a pt-PT accent) through 0.90 (too loose). At 0.90, with the TV on, the panel
  woke **by itself** and sent TV speech to the assistant. 0.93 is the middle.
- The model is trained in English; a non-English accent is exactly why it needs a
  more permissive cutoff than the default.
- `ok_hermes` was trained in Portuguese, so it needs no such compromise (0.5) and
  is the safer phrase in a room with a TV on.
- If false triggers return, the right fix is **training a model to your own
  voice** on the library site above — not tightening the cutoff, which ends up
  missing real commands.

## Diagnosing a trigger

- The board log is **not persisted**, so look first at the **"Last wake word"**
  `text_sensor` (model + timestamp of every trigger). That sensor exists
  precisely because an "invisible" wake-up had no evidence.
- Distinguish wake word from push-to-talk: if `binary_sensor.<board>_button` was
  `off` over the period, the button was not touched → it was a local detection.
- The `mwwdiag` interval logs engine and per-model state every 60 s, plus the
  voice-assistant state (`va_state`) and how long it has been in it — that is
  what shows a stuck state (see `troubleshooting.md`).

## Wake word + I2S bus

The wake word engine holds the shared I2S bus while listening: the firmware stops
the engine on `on_start` and restarts it only when audio has *really* finished
(`on_tts_stream_end`). Never use `on_end` for that — it fires tens of seconds
before playback ends, which produces silent speech. See `audio.md`.
