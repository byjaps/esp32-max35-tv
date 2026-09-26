# Voice latency — what was measured and what was changed

A voice assistant feels broken when a simple command takes 20 s. This page keeps
the measurements and the fixes, split by **where each one lives**, because the
fastest wins are not in the firmware at all.

Rule of thumb from all the numbers below: **the panel and the transcription are
almost never the problem — the path the sentence takes to an LLM is.**

## 1. Panel firmware: a stuck voice state used to mute the panel

Symptom: the panel answered a command and then went **deaf** — no wake word, no
reaction — until it was power-cycled. Measured once: stuck for **3 min 15 s**,
while HA's own side had already finished (satellite back to `idle`, media player
`off`).

Cause: the engine guard only restarts wake-word detection when the panel's own
voice state is `0` (`idle`). If the state machine ever ends up elsewhere, the
guard never runs and the panel stays muted forever.

Fix (v0.15.3, in this repo's YAML): a **watchdog** in a 2 s `interval` — it
records when the state last changed (`va_estado_ms`) and forces the state back to
`0` when a state has been held far longer than possible:

| State | Limit |
|---|---|
| listening | 45 s |
| thinking | 180 s |
| speaking | 90 s |
| error | 15 s |

It never cuts in while the speaker is playing or announcing, and on recovery it
repaints the screen and calls `mww_resume` (which re-enables both wake-word
models — see `wake-word.md`).

## 2. Satellite (Home Assistant): try locally before paying for an LLM

With the Hermes conversation component, every sentence used to be forwarded to
the agent unless it was a plain home command. Changes made there (upstream
project: [`byjaps/hermes-voice-ha-integration`](https://github.com/byjaps/hermes-voice-ha-integration)):

| Case | Before | After |
|---|---|---|
| `turn on the small light` (plain command) | ~0.1 s | **0.01-0.2 s** (unchanged, already local) |
| `turn on the small light. turn it off.` (two commands in one sentence) | 16 s (agent) | **0.29 s** — each clause resolved locally, then combined |
| `turn off the small light. what time is it?` (command + question) | 27 s (agent) | **0.03 s** |
| `[BACKGROUND TEAM SOUND]` / `♪ ♪` (pure noise transcribed as a marker) | 5.2 s (agent, answering "didn't get that") | **0.00 s** — answered locally without waking the agent |
| A trailing hallucinated phrase glued to a real command | 8-19 s (agent) | **0.02-0.2 s** — the tail is stripped, but only after the HA intent parser confirms the remainder still means something |

The safety rule in all of it: a clause is only dropped or handled locally when
the intent parser recognises the remainder **without executing anything** — so a
sentence holding two real commands is never half-executed.

## 3. Phrases the HA parser doesn't know: config, not code

`what time is it` was answered in 0.2 s; `can you tell me the time?` cost 7.6 s
because it fell outside the built-in sentence list and went to the LLM.

Adding variants is a **configuration file**, not a code change:
`/config/custom_sentences/<lang>/<name>.yaml` listing extra sentences for an
existing intent, applied live with the `conversation.reload` service. Measured
after: 0.00-0.08 s. Include the **unaccented form** of the phrase too — the
built-in list only has the accented one while STT sometimes returns it flat.

## 4. The agent itself: the two settings that mattered

Measured with the same question, same session, only the model's reasoning effort
changed (the agent is the Hermes Agent CLI, invoked per voice turn):

| Reasoning effort | Total | What the log showed |
|---|---|---|
| `low` | **28.0 s** | first call: 42 k input tokens, 322 output tokens, 22.3 s latency — i.e. seconds spent *thinking* before even picking a tool |
| `minimal` | 18.0 s | 4 tool round-trips |
| `none` | 8.7 s | 2 calls — **but** the model started bailing out with "didn't get that" on data questions instead of calling tools (`out=5` tokens, no tool call) |

So the recommendation for voice turns is **`minimal`** plus **`--max-turns 4`**
(it was 8, which is how a light that does not exist produced a 40 s timeout: eight
failing round-trips in a row). `none` is faster but loses answers — do not use it
for questions that need a tool.

**And one real bug on the tool side:** the "is it going to rain?" question came
back in 20 s with "didn't get that", because the weather service was called
without `?return_response` — HA answers `400 Service call requires responses but
caller did not ask for responses` and the agent, with no data, burned its turns.
With that fixed the same question answers in **4-10 s** with the actual forecast.

## 5. What was NOT the bottleneck

- **Speech-to-text.** whisper.cpp transcribes in streaming: for commands handled
  locally, HA's satellite goes from "listening" to "responding" within the same
  second. Do not spend an evening tuning the STT add-on for "it's slow".
- The number of tool turns a *correct* answer needs (2 is normal).
- The 42 k-token prompt: its prefill is ~2 s per call — real, but an extra
  round-trip costs more than the prefill.

## 6. How to measure your own setup

- The satellite's state history in HA (`listening → processing → responding`)
  gives the total per interaction; the gap between `processing` and `responding`
  is what the assistant side costs.
- The agent's own log has one line per model call: `API call #N: in=… out=…
  latency=…` — that tells you instantly whether you are paying for input,
  reasoning, or extra round-trips.
- A sentence that "isn't understood" in 3-5 s with almost no output tokens was
  never attempted: check the tool call, not the model.