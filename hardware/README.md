# Hardware — MAX35-TV official resources

The board is the **Spotpear ESP32-S3 MAX35-TV** (`ESP32S3-MAX35-TV-W`).

## Official wiki

- **User guide (Spotpear wiki)**: https://spotpear.com/wiki/ESP32-S3-3.5-inch-LCD-TV-Display-Deepseek.html
  — first-run XiaoZhi usage, wake word, SD video/music, Pomodoro clock,
  wallpaper, factory firmware restore, and the hardware documentation links
  below.
- **Product page / shop**: https://spotpear.com/shop/ESP32-S3-3.5-inch-LCD-TV-Display-Deepseek.html

## Official hardware documentation

| Document | What it is |
|---|---|
| [`ESP32S3-3.5inch-AI-1_hardware.pdf`](ESP32S3-3.5inch-AI-1_hardware.pdf) | Board schematic (power latch, battery divider, USB divider, pinout) |
| [`ST7796S_Datasheet.pdf`](ST7796S_Datasheet.pdf) | Display controller datasheet |
| [`GT911_Datasheet.pdf`](GT911_Datasheet.pdf) | Touch controller datasheet (not present on the revision this firmware targets) |
| `ESP32S3-3.5inch-AI.DWG` | 2D board outline (CAD) — [official link](https://cdn.static.spotpear.com/uploads/picture/learn/ESP32/ESP32S3-MAX35-Only-Board/ESP32S3-3.5inch-AI.DWG) |
| `ESP32S3-3.5inch-AI.step` | 3D board model (STEP) — [official link](https://cdn.static.spotpear.com/uploads/picture/learn/ESP32/ESP32S3-MAX35-Only-Board/ESP32S3-3.5inch-AI.step) |
| `OV5640` / `GC0308` camera model PDFs | Camera module specs — [link](https://cdn.static.spotpear.com/uploads/picture/learn/ESP32/ESP32S3-MAX35-Only-Board/OV5640camera%20model%20.pdf) |
| Factory firmware | `ESP32S3-MAX35-TV-EN.bin` (16 MB, offset 0x0) + `flash_download_tool-2.zip` — [wiki](https://spotpear.com/wiki/ESP32-S3-3.5-inch-LCD-TV-Display-Deepseek.html) |

(Larger binaries — factory firmware, flash tool, DWG, STEP — are download-only
to keep this repo lean; use the official links above. See `LINKS.md`.)

## Key hardware facts this firmware relies on

- **Battery**: ADC on **GPIO6**, 1:1 divider (R57 100K / R60 100K), so
  `multiply: 2.0`. Li-ion 3.30–4.20 V.
- **USB sense**: ADC on **GPIO7**, divider R59 20K / R61 30K (`multiply: 1.6667`).
- **Power button**: on the **latch circuit**, no GPIO → cannot be read or
  controlled by firmware.
- **Codecs**: ES7210 (mics) + ES8311 (speaker) on a shared I2S bus, clocks
  driven by the ESP32-S3. No jack / no line-out; the ES8311 drives only the
  onboard speaker.
- **Bluetooth**: BLE 5.0 only — never pairs with speakers/headphones (no A2DP,
  no LE Audio until BLE 5.2). A2DP-class audio out should go through HA to a
  BLE-capable speaker instead.

## Reference ESPHome config (authoritative pins)

The pins/wiring in the firmware are verified against the manufacturer's own
ESPHome file:

- `RealDeco/xiaozhi-esphome` → `devices/Under_Development/Modular/HW/spotpear-tv_hw.yaml`

Use that as the source of truth for any peripheral work. Do not trust third-party
(or LLM-generated) pinouts for this board.