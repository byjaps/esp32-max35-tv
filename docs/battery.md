# Battery

## How it is read

No fuel gauge on the I2C bus (only ES8311 `0x18`, ES7210 `0x40` and the camera
`0x3C`). The battery is read by **ADC on GPIO6** with a 1:1 divider (confirmed
in the schematic: V_BAT → R57 100K → GPIO6 → R60 100K → GND):

- `sensor.esp32_max35_tv_battery_voltage` — raw V, `multiply: 2.0`
- `sensor.esp32_max35_tv_battery` — % from a Li-ion curve:
  **3.30 V = 0 % ... 4.20 V = 100 %** (linear)

## Why it "never reaches 100 %"

100 % (4.20 V) **only exists while charging** — it is the voltage the charger
imposes. Once charging ends, with the panel consuming, the cell settles at
4.02–4.10 V = 80–88 %. That is correct, not a measurement error. Don't "fix"
the scale to make a full battery read 100 %.

## Charging status

- **The red LED is not usable** to tell charging — it is tied to the charger's
  CHG pin, not a GPIO, so the firmware cannot read it.
- The firmware instead reads **USB voltage on GPIO7** (`USB voltage` sensor) and
  exposes `binary_sensor..._charger_connected`.

## Charging diagnosis, first step first

A battery stuck at ~88 % (4.09–4.11 V), with the red LED only flickering, is
almost always the **power source**, not the battery/board. A charger that
delivers less than 5 V at the panel has no headroom to charge and run at once.
Measured: with a weak source the voltage sat at 4.11 V (~88 %); with a **3 A
charger at 5.10 V** it climbed 4.094 → 4.182 V (88 % → 98 %) in ~1 min.

**Always test with another charger/cable (≥3 A, short) and confirm `USB voltage`
> 5 V before blaming anything else.**

## Repo scripts (see `scripts/`)

- `vigia-bateria.py <min>` — sample the battery every 30 s and watch the trend
  (a rising voltage while charging = healthy; flat/dropping = not charging).
- `regista-bateria.py` — log battery values over time.
- `gestor-bateria-painel.py` — battery manager.