# Audio

This board's audio is the tricky part. Two codecs share **one I2S bus**:
ES7210 (dual mic, ADC) and ES8311 (speaker, DAC), on a single `i2s_audio` bus
with one mutex. The wake word engine also claims that bus while listening.
Most "sound" problems trace back to contention or a sample-rate mismatch, not
a bad component.

## Golden rules

1. `speaker.sample_rate` == `audio_dac.sample_rate` == `microphone.sample_rate`
   == **16000**. A mismatch makes the DAC misread the clock and emit "strange
   noise". (An earlier revision ran 48000 on the speaker vs 16000 on the DAC.)
2. The speaker volume starts at **1.0 = 0xFF on the ES8311 = saturation**. The
   firmware pins it back to 0.75 (0 dB) in `on_boot` at `priority: -100`
   (runs after the speaker setup).
3. The two volume controls (HA `number` and the media player) both write to the
   same speaker and each kept its own value — they diverged (65% vs 82%). The
   firmware keeps **one** source of truth (`vol_pct`) and syncs by event, never
   by polling (the media player discards volume sets when its queue is full).

## The I2S bus and the wake word engine

If the media player starts while the engine is listening:

```
[E][i2s_audio.speaker.std:401]: Parent bus is busy
[E][i2s_audio.speaker:115]: Driver failed to start; retrying in 1 second
```

And if nothing ever releases the bus, the board seizes up. The fix is a
**lock** (`mp_playing` global) + triggering on **`on_turn_on`** (fires when the
command arrives, before the pipeline plays) — `on_play` is too late, it never
fires while the bus is held. See `media-player.md`.

## Distorted voice: characterize before changing anything

`parent bus is busy` / saturating audio are different failures. Isolating test:
the `Sound test` button (`rtttl`) plays a melody through the speaker without
the voice pipeline.

- **Melody = pure hiss/static** → codec/clock problem (check sample rates).
- **Melody = a clean note** → the DAC works but gain/voice-shaping may still be
  wrong — a saturated *tone* still sounds like a note; only *speech* becomes
  unrecognisable. A "zumbido/static" verdict is **saturation**, not speed or
  stutter.

## TTS format

The panel declares `voice_assistant: speaker:`, so the HA pipeline keeps TTS at
**WAV / 16000 Hz mono** regardless of what the media player declares. Do not
copy the manufacturer's FLAC 48 kHz media setup — that assembly has a 48 kHz
bus and resamplers, which this one does not. The media player uses `WAV/16000/1`
in this config and HA transcodes everything to it.

## Conversation timeout (`conversation_timeout: 5s`)

ESPHome's default is **300 s**: for 5 minutes after a reply the panel keeps
accepting speech **without** the wake word — catching TV/house noise,
transcribing junk, and pushing it to the (slow) agent. This firmware sets 5 s.
Never raise it back to the default.