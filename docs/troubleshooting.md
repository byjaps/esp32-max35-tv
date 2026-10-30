# Troubleshooting — the hard-won pitfalls

Each of these cost real debugging time. Read before re-diagnosing.

## 📦 Build/version

### ESPHome 2026.10.x — the early reboots were post-flash settling, not a defect

The first 2026.9.x build rebooted every ~60 s (log: uptime 3.4 s → 63.5 s →
2.5 s) and the bootloader even did a silent **rollback** to the previous
build. That looked like a version bug, but it was **post-flash settling**: the
board rebooted 2–3 times in the first ~45 min after each flash and then settled
— measured 1 h 16 min of continuous uptime, and later builds ran stable for
**2 h 45 m+**. The current firmware (**v0.17.14**) runs **ESPHome 2026.10.0**
in production, stable. **Do not pin to 2026.8.2 or 2026.9.0** — the current
build is the one in use.
Still confirm `esphome version` before compiling and watch 3–4 min after any
flash (see below).

### A "successful" OTA that boots the old version is a ROLLBACK

If the log shows the old version after a supposedly-good upload, the new
firmware crashed before marking the boot as good (`safe_mode`):
`OTA rollback detected! Rolled back from partition 'app1'`. Confirm the actual
running version before concluding anything. Addresses in the crash resolve
against the crashing build's ELF with `xtensa-esp32s3-elf-addr2line`.

### After any flash, watch 3–4 min (version + uptime)

A build that reboots before ~60 s rolls back on its own and the old firmware
returns; one that passes 60 s has marked the boot good and will keep
rebooting `forever` without rollback. Don't call a flash "done" until you've
seen a stable window.

### `ota: encryption:` — the CLI is fail-closed

With `ota: encryption:` in YAML and the board running old plaintext OTA, the
CLI refuses ("refusing to send the image in plaintext"). Upload with a temp
copy of the YAML without the `encryption:` block (keep `api: encryption:`), or
just understand the transition order: the 2026.9.x bring-up goes in
plaintext; `encryption:` only goes in after the log shows
`Encryption: offered, plaintext accepted`.

## 🔊 Audio

### Wake word coming back only a minute after a reply — never gate on the speaker state

A regression worth knowing by name, because the wrong fix looks right.
`mww_resume` was changed to require `!id(box_speaker).is_running()` before
restarting the wake word engine, on the theory that `on_tts_stream_end` fires
when Home Assistant finishes *sending* the audio — so the engine would grab the
shared I2S bus and cut the reply mid-word. **The theory is wrong.** In
`voice_assistant.cpp` (`State::RESPONSE_FINISHED`) the trigger only fires once
`speaker_buffer_size_ == 0` **and** `!has_buffered_data()` **and**
`!is_running()` — that is, when all the audio has already come out of the
speaker — and `speaker_->stop()` is called immediately before it. On top of
that, `is_running()` stays true far longer than the playback lasts, so the
retry loop never succeeds: the engine only came back through the 60 s interval
safety net. Measured symptom: *"only about a minute or more later does it hear
Okay Nabu again"*. Reverted (v0.15.8). The guards that belong there are the ones
already present: `mp_playing` and `va_state`.

If a reply is ever cut mid-word, **measure the audio before touching the
firmware**: the pipeline's own cache file in Home Assistant (`/config/tts/`, the
name starts with the sha1 of the spoken text) and its duration with `ffprobe`.

### `Parent bus is busy` loop, board seizes up

Mic and speaker share one I2S bus (one mutex). If the wake word engine holds it,
the speaker can't start and retries forever; if nothing releases the bus the
board stops responding to WiFi. **Fix: `on_turn_on` trigger + `mp_playing`
lock** — never rely on `on_play` (too late) or `on_end` (too early). See
`media-player.md`.

### Screen stuck on "speaking", no sound at all (v0.15.15)

Log signature, once per second:

```
[E][i2s_audio.speaker:115]: Driver failed to start; retrying in 1 second
[E][i2s_audio.speaker.std]: Parent bus is busy
```

Home Assistant asked for a TTS reply, the wake word engine was holding the I2S
bus, so the speaker never started — and without `on_tts_stream_end` the voice
state stayed on `speaking` forever. The normal watchdog does **not** rescue this
because it counts from the last state *change*, and the state never changes.

Three fixes, all in this repo's YAML:

- `micro_wake_word.stop` in **`on_tts_stream_start`**, before the first byte, and
  in the 2 s interval whenever the voice state is `thinking`/`speaking`;
- the "nobody spoke" branch no longer restarts the engine by hand — `on_end`
  does it (2 s delay + state check), the proven path;
- a new guard: a TTS request pending for **>15 s** with
  `box_speaker.is_running()` false → stop the engine, repaint idle and
  `mww_resume`.

### Red error icon every time you stay silent (v0.15.14)

When the VAD triggers on noise and nobody speaks, the STT returns an empty
string and Home Assistant ends the pipeline with the error
**`stt-no-text-recognized`** (`assist_pipeline/default_pipeline.py`). The
`on_error` handler used to paint the error state (red ring, 15 s) for what is
just silence. This repo treats that code as "nobody spoke" — back to idle and
the wake word engine, no alarm. Any other code is still a real error.

### Distorted / "strange noise" speech

- First: `speaker.sample_rate` must equal `audio_dac.sample_rate` and the
  microphone's — all **16000**. 48000 vs 16000 = DAC misreads the clock.
- Second: the speaker starts at volume **1.0 = saturation**. The ES8311 driver's
  0 dB point is 0.75; above that speech distorts while tones still sound like
  notes. Check `on_boot` re-pins the volume.
- Use the **Sound test** button to isolate: pure hiss = codec/clock; clean note
  = DAC ok but gain/shape wrong. See `audio.md`.

### Hear audio after the screen says "done"

`on_tts_end` / `on_end` are NOT playback end — they can fire **tens of seconds
before** the audio finishes. Using them to restore "idle" / restart the wake
word engine leads to the engine grabbing the bus mid-play: screen says
"speaking", nothing is heard. Use **`on_tts_stream_start`/`on_tts_stream_end`**.

### "It hears too much / slow to answer"

`conversation_timeout` default is **300 s** — the panel accepts speech without
a wake word for 5 minutes, catches TV/house chatter, transcribes junk and sends
it to the (slow) agent. Set `conversation_timeout: 5s`. Also keep
`volume_multiplier` at 1.0 (2.0 raises noise to ~40 % of scale and breaks VAD).

## 🎙️ Wake word

### The wake word never starts by itself

`micro_wake_word` does **not** auto-start in ESPHome ≤2026.8. The action is
required in `on_boot`, and `start()` silently refuses until the component is in
the loop phase (`is_ready()`) — so the `delay: 10s` before the start is
**mandatory** (on_boot runs during setup). No log line, just nothing.

### Wake word fires with the TV on

`okay_nabu` is permissive enough to accept ambient speech. Look at the
**"Last wake word"** `text_sensor` first (the board log isn't persisted). If
false triggers return, raise `probability_cutoff` (0.93 → 0.95) or **train a
custom model** (a pt-trained model needs no such compromise — see
`wake-word.md`), don't jump straight to a tighter cutoff (it misses real
commands).

### The second wake word never fires

ESPHome enables only the **first** entry of `models:` (`default_enabled = i == 0`);
any further model boots **disabled, with no error at all**. The config must call
`micro_wake_word.enable_model` for each model (this repo does it in `mww_resume`
and re-checks in the 60 s `mwwdiag` interval). The interval log prints each
model's state — if it says `OFF`, that is why the phrase does nothing.

Related: Home Assistant **disables every model** when it configures the satellite
and re-enables only the ones in its `active_wake_words` list. If the wake-word
selects in HA read `no_wake_word`, the list is empty and all models are off. The
same interval log tells the two situations apart.

### The panel goes deaf after answering (stuck voice state)

If the panel answers and then ignores everything (no wake word, no reaction) until
it is power-cycled, the voice state machine is stuck: the engine guard only
restarts detection while the state is `idle`, so a stuck state mutes the panel
permanently. The **watchdog** in the 2 s `interval` (this repo's YAML) forces the
state back and restarts the engine — it never cuts in while the speaker is
playing. To confirm it on an older build, check the `mwwdiag` log line for
`va_state` and how long it has been held. Details: `performance.md` §1.

## 🔋 Battery / power

- **"Never reaches 100 %"** is normal outside charging (see `battery.md`).
- **Charging stuck at ~88 %** → almost always the power source. Test another
  ≥3 A charger/cable and confirm `USB voltage` > 5 V before blaming anything.
- **Unexpected reboots** → read `Last reset reason` sensor
  (`software via esp_restart` = clean software request; `brownout` = power;
  `panic` = crash). This sensor exists precisely to distinguish these.

## 🔌 Other

- **Panel plugged into a laptop USB port** can trip overcurrent protection and
  kill the whole USB bus (Bluetooth + mouse). Use a powered hub for cable
  flashes.
- **"Is it hanging? Ping is failing."** A failing ping does not mean the panel
  is down — test the API port directly:
  `python3 -c "import socket;socket.create_connection(('<ip>',6053),timeout=3)"`.
  Only if that fails is the device actually down.
- **Don't `pkill -f` an ESPHome build** — the pattern matches your own shell,
  killing the build you meant to keep. Kill by PID.
- **Never trust LLM-generated ESPHome config for this board** — pins/codec/PMIC
  have been invented before. Verify against the manufacturer's
  `spotpear-tv_hw.yaml`.