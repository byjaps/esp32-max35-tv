# Setup — flash the panel and wire it to Hermes

## 1. First flash (cable, one time only)

The board ships with **XiaoZhi** firmware. Replace it with ESPHome. Use
[ESPHome Web](https://web.esphome.io) in Chrome/Edge (no install — it detects
the USB-serial port). Recommended laptop workflow:

1. **Dump the original flash first** (to preserve XiaoZhi):
   `esptool.py read_flash 0 0x400000 xiaozhi-original-4MB.bin`
2. Flash the factory image. Compile it yourself (`esphome compile
   esp32-max35-tv.yaml` → `.esphome/build/<name>/build/firmware.factory.bin`)
   and write it over the cable:

   ```bash
   esptool.py --chip esp32s3 --port /dev/ttyACM0 write-flash 0x0 firmware.factory.bin
   ```
3. The board joins your WiFi and connects to HA.

> ⚠️ **Power the board from a powered USB hub, never a bare laptop USB port.**
> The MAX35-TV has tripped a laptop's overcurrent protection, killing the whole
> internal USB bus (Bluetooth + mouse included), which then needs a reboot to
> recover. Use a powered hub for the cable flash.

## 2. Build + OTA (everything after the first flash)

Once the board has ESPHome + WiFi, all updates are over the air — no cable ever
again. From the directory holding your `secrets.yaml` and this YAML:

```bash
esphome run esp32-max35-tv.yaml
```

No toolchain on hand? Compile on any machine with ESPHome installed and hand the
resulting `.esphome/build/<name>/build/firmware.ota.bin` to the **ESPHome**
add-on/Web dashboard — same result, no local toolchain on the machine driving the
board.

> ✅ **ESPHome 2026.9.0 is the current, supported build** — the board runs it
> stable (see `troubleshooting.md`). Validate first: `esphome config`.

## 3. Home Assistant side

The board speaks to HA as an **Assist satellite**. On the HA side you need:

1. The **[`rusty4444/hermes-voice-ha-integration`](hermes/README.md)** component
   (via HACS) + the Hermes `home_assistant` and `voice_stack` plugins running on
   Hermes, so Hermes registers as a **Conversation Agent** in HA.
2. An **Assist pipeline** whose conversation agent is **Hermes**.
3. The panel selected as the satellite that uses that pipeline.

With that in place:
- **Push-to-talk**: press the BOOT button ≥600 ms, speak, release. Works
  always and is the guaranteed fallback.
- **Wake word**: say "okay nabu" (see `wake-word.md`).

## 4. Entities you get

Key entities from this firmware (names in the YAML — the `object_id` follows the
`name:` you give the device, so `<board>` below is `esp32_max35_tv` if you keep
the defaults):

| Entity | Description |
|---|---|
| `media_player.<board>` | panel speaker — announcements, TTS, radio |
| `number.<board>_speaker_volume` | the one source of truth for volume |
| `sensor.<board>_battery` | battery % |
| `binary_sensor.<board>_charger_connected` | charger status |
| `text.<board>_media_title` | what is playing (written by HA) |
| `text_sensor.<board>_firmware_version` | firmware + ESPHome version (diagnostics) |
| `text_sensor.<board>_last_wake_word` | diagnostics — which model fired, when |
| `text_sensor.<board>_last_reset_reason` | diagnostics — software/watchdog/brownout/panic |

## 5. TTS announcements from HA (`tts.speak`)

To say a one-off message on the panel without going through the voice pipeline:

```json
POST /api/services/tts/speak
{
  "entity_id": "tts.<your_tts_service>",
  "media_player_entity_id": "media_player.esp32_max35_tv",
  "message": "...",
  "cache": false
}
```

The lock/release logic (see `media-player.md`) stops the wake word engine on
its own — nothing needs to be stopped manually.

## 6. Set priorities

- `conversation_timeout: 5s` is set in the YAML on purpose — never leave the
  ESPHome default (300 s), or the panel accepts speech without the wake word
  for 5 minutes and hears too much.
- The HA integration handles "instant local answers" for simple queries —
  see `hermes/README.md`.