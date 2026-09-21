# Media player

The panel speaker is exposed to HA as a `media_player` (`media_player.esp32_max35_tv`),
so it can play announcements, TTS messages and radio/music. From the ESPHome
side it is `platform: speaker` with a single `announcement_pipeline`
(`WAV/16000/mono`).

## The `on_turn_on` trigger (the trap)

The shared I2S bus is held by the wake word engine while listening. If the
media player starts with the engine running, the speaker fails with
`Parent bus is busy` in a loop and the board can **seize up**.

- **`on_play` is too late**: it only fires when the pipeline actually starts
  playing — which never happens while the bus is held → permanent deadlock.
- The firmware uses **`on_turn_on`** (fires the instant the command arrives,
  before the pipeline plays) → `mp_stop_wake` releases the bus, and
  **`on_idle`** returns the player to `OFF` so the next command re-fires it.
- Every path that could restart the engine is guarded by `mp_playing`, and the
  60 s interval is a safety net that unlocks if a media command dies without
  ever playing (dead URL, source down).
- The assistant TTS also passes through this media player's announcement
  pipeline, so `mp_playing` is true during **every spoken reply** — the screen
  only shows the media view when `va_state == 0` (not mid-conversation).

## Showing what is playing

The ESPHome media player does **not** receive metadata from HA (title, artist,
station) — the API only carries the URL. The firmware exposes a `text` entity
(`Media title`); HA writes the resolved title there (`text.set_value` — note:
`text.set_value`, there is no `text.set` in HA; using the wrong name returns
HTTP 400 and opens a repair warning), and the media screen shows it. If empty,
that, it falls back to "Radio / Music". Deriving a readable name from
`media_content_id` is done in a HA template (see the note in the YAML history).

## Announcements / TTS

`tts.speak` works directly — the lock logic stops the wake word engine on its
own. See `setup-hermes.md` §5 for the exact call. `media_player.media_stop` is
the way to stop playback; there is **no `turn_off` / `pause`** supported by this
component (they return HTTP 500).

## Volume

Two HA controls target one speaker. The firmware keeps a single source of truth
(the `number`), sized UI-scale with an audible floor and a distortion ceiling,
synced to the media player **by event** (`on_volume`) — never by polling (the
component discards volume sets when its queue is full). See `audio.md`.