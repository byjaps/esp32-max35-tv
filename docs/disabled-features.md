# Disabled features

This firmware intentionally does **not** enable every feature the MAX35-TV
hardware has. This documents what is off and why, so nobody assumes the board
has working camera / SD / touch.

## Camera (disabled)

The `esp32_camera` block is **commented out** in the YAML. Reason for removal:

- The board has **no IR LED** — it sees nothing at night, so it was not useful
  as a motion sensor.
- ESPHome has **no image-based motion detection**; the home already has a
  dedicated camera for that.
- Keeping it cost **12 KB RAM, 65 KB flash and ~1.2 MB PSRAM**.

**Re-enable:** uncomment the `esp32_camera:` block in the YAML. The pins are
from the manufacturer's official file. Note the camera shares the I2C bus; when
it initialises it adds a `0x3C` address to the I2C scan — that is the camera
(SCCB), not a new device or touch.

## microSD card (not configured)

The SD slot exists on the board but is **not configured** in this firmware (the
`spi:` block has only `clk`/`mosi` for the display, no SD slot). SD *video* and
*music* playback are features of the original **XiaoZhi** firmware and do not
exist here. There is nothing to re-enable unless you add an `sd_mmc_card`
component and the corresponding logic.

## Touch (no GT911 on this revision)

This device revision has **no touchscreen** — the GT911 controller does not
exist / does not respond, and the manufacturer's official ESPHome config does
not define it either. The panel is voice + HUD. The touchscreen block is
removed; if touch hardware is ever confirmed, the block to restore is (see YAML
note):

```yaml
touchscreen:
  - platform: gt911
    i2c_id: bus_a
    address: 0x5D|0x14
    display: main_display
```

## Power button (hardware, not firmware)

The case has a POWER button, but it is **not on any GPIO** — it lives in the
power-latch circuit (IC U1 + Q1/Q2 APM2307 + the `Power_EN` net). The firmware
cannot read it, give it gestures, or power the panel down by software. Power
on/off is purely the latch electronics, whatever you do in firmware.