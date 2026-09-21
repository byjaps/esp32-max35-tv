# Hermes as the HA Conversation Agent

This directory documents the integration that makes the whole thing work: the
panel is the hardware, **Hermes is the brain**.

## What it is

[`rusty4444/hermes-voice-ha-integration`](https://github.com/rusty4444/hermes-voice-ha-integration)
is a HACS component (author: **Sam Russell / rusty4444**) that registers Hermes
Agent as a selectable **Conversation Agent** in Home Assistant's Assist
pipelines. Once selected:

- wake word / push-to-talk → **local STT** (whisper.cpp) → **Hermes** handles
  the conversation → **TTS** back on the panel speaker.
- It runs on local hardware, no cloud, no subscription, no added latency from
  an external service.

The flow is:

```
MAX35-TV (ESPHome, this repo)
   → Assist pipeline (STT / TTS on the HA side)
   → Conversation Agent = Hermes
      ← rusty4444/hermes-voice-ha-integration (HACS)
   → Hermes Agent ↔ HA (voice_stack + home_assistant plugins)
```

## Install

Follow the author's README. In short:

```bash
python3 -m pip install --upgrade "hermes-voice-ha-integration @ git+https://github.com/rusty4444/hermes-voice-ha-integration.git@v0.0.12"
```

or install via HACS in Home Assistant. Then configure Hermes's WebSocket URL /
token so HA reaches Hermes, enable the `home_assistant` and `voice_stack`
Hermes plugins, and pick **Hermes** as the conversation agent of your Assist
pipeline.

## Local intent answers (opt-in)

The integration has an **instant local answer** mode: simple house queries
(room temperature, entity state, date/time, timer status) are answered in
milliseconds on the HA side, bypassing the slow path to the agent entirely —
which also stops whisper transcription junk from breaking intent matching.
It supports `off` / `answers` / `commands`.

## Contribution

This setup includes two `byjaps` PRs merged upstream:

- [#42](https://github.com/rusty4444/hermes-voice-ha-integration/pull/42) —
  WebSocket reconnect robustness.
- [#46](https://github.com/rusty4444/hermes-voice-ha-integration/pull/46) —
  instant local answers (and stopping whisper noise from breaking intent
  matching).

**That component is upstream software — please direct issues, feature
requests and contributions to the author's repository, not here.** This folder
only documents how the panel and Hermes are wired for this project.