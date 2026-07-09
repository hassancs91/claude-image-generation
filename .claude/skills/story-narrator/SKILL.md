---
name: story-narrator
description: Generates one expressive narration MP3 per scene for an English storybook, using the ElevenLabs MCP (text_to_speech). Reads {slug}_scenes.json (from scene-splitter), proposes a warm storyteller voice, drafts the narration text per scene (optionally with Eleven v3 audio tags for emotion), lets the user review, then generates one MP3 per scene saved as {slug}_part_NN.mp3 so it pairs by index with the scene's image. Use this skill whenever the user wants to narrate a story, generate per-scene audio, voice a storybook, create read-along narration, or produce TTS for the storybook pipeline. Trigger on phrases like "narrate this story", "generate the audio", "voice the storybook", "make the narration", "read this story aloud", or whenever scenes.json exists and the user wants spoken audio. Requires the ElevenLabs MCP connected.
---

# Story Narrator

Turns a story (already split into scenes) into a set of expressive narration clips — **one MP3 per scene** — using the ElevenLabs MCP. Each clip is saved as `{slug}_part_NN.mp3` so it pairs by index with the scene's image: scene 3's picture and scene 3's narration play together in the final storybook.

## When this skill applies

`{slug}_scenes.json` exists (from `scene-splitter`) and the user wants per-scene audio. Also applies if the user pastes a story and asks to narrate it — split it first (or narrate paragraph-by-paragraph).

The skill does NOT apply to:
- A single short utterance (call `text_to_speech` directly).
- Real-time conversational TTS, music, or sound effects.
- Voice cloning (do that separately in ElevenLabs, then bring the `voice_id` here).

## Required tool — the ElevenLabs MCP

The skill calls **`mcp__elevenlabs__text_to_speech`**. Confirm it's available before Stage 4. If the MCP isn't connected, tell the user to install it (`uvx elevenlabs-mcp` with `ELEVENLABS_API_KEY` set — see https://github.com/elevenlabs/elevenlabs-mcp) and stop. Stages 1–3 (voice choice + narration script) work without it; only generation needs it.

Key `text_to_speech` parameters this skill uses:
- `text` — the scene's narration text
- `voice_id` (or `voice_name`) — the chosen storyteller voice
- `model_id` — see Stage 2 (default a v3 model for audio-tag expressiveness; fall back to `eleven_multilingual_v2`)
- `stability` — `0.4`–`0.5` for natural, expressive delivery (lower = more emotional range)
- `style` — small positive value (e.g. `0.2`) adds expressiveness; `0` is flat
- `output_directory` — set to the story's audio folder so files land in the right place

The MCP **saves the file and returns its path** — it names the file itself, so this skill **renames** each result to the locked `{slug}_part_NN.mp3` convention after generation (Stage 5).

## Workflow — five stages with one hard gate

### Stage 0: Load scenes.json

Read `{slug}_scenes.json`. Treat each scene's `text` as one narration clip. Use each scene's `mood` to guide delivery/tag choices. The clip for `scenes[i].index = N` becomes `{slug}_part_NN.mp3`.

### Stage 1: Intake and analysis

1. Read all scene texts.
2. Note total characters (rough cost = chars × ~$0.10/1k) and how much is dialogue.
3. One-line summary: "N scenes, ~C total characters, ~D% dialogue. Recommendation: single narrator."

### Stage 2: Voice strategy and selection

Propose **single narrator** (the default and best choice for beginner storybooks — one warm voice carrying the whole story, shifting tone for dialogue). Only consider per-character voices if dialogue is heavy AND there are 2+ distinct recurring speakers AND their voices should clearly differ — and even then, single narrator usually sounds more cohesive for a short children's story.

**Voice choice:**
- If the user already has a preferred `voice_id`, use it.
- Otherwise, suggest finding a warm, friendly storyteller voice. You can call `mcp__elevenlabs__search_voices` (e.g. search "storyteller" or "warm narration") and propose ONE specific voice with its `voice_id`. Don't list five.
- Ask once if needed: "What `voice_id` should I use? (Find one in your ElevenLabs library, or I can search for a warm storyteller voice.)" Suggest the user save it for future runs.

**Model choice:**
- Default to **`eleven_v3`** (most expressive; supports `[warmly]`-style audio tags). If the account/MCP doesn't support v3, fall back to **`eleven_multilingual_v2`** (no audio tags — rely on `stability`/`style` for expressiveness). State which one you're using.

Pause: "Voice: [name + id]. Model: [v3 / multilingual_v2]. Single narrator. Reply `go`, or tell me what to change."

### Stage 3: Narration script (+ optional emotion tags)

For each scene, prepare the narration text:
- **original** — the scene's `text`, unchanged
- **tagged** — only if using `eleven_v3`: the same text with a few audio tags inserted to match the scene's `mood`. Use sparingly (1–2 tags per scene). Useful tags: `[warmly]`, `[softly]`, `[gently]`, `[cheerfully]`, `[curiously]`, `[whispering]`, `[excited]`, `[sadly]`, `[reassuringly]`. Place a tag BEFORE the text it affects; it persists until the next tag. Use `...` for natural pauses. Don't over-tag — it reads choppy.
  - If using `eleven_multilingual_v2`, skip tags entirely (it ignores them / reads them aloud). Expressiveness comes from `stability`/`style` and the voice itself.
- **rationale** — one line on why those tags fit (only when tagging)

**Title clip (recommended).** Produce a short separate `title.mp3` from the bare story title with one warm tag (`[warmly] The Little Cloud.`). The publisher plays it on the dedicated cover page (slide 0) before auto-advancing into scene 1, so the cover isn't silent — generating it is worth the one extra clip. Keep it minimal. Save it as `{slug}_audio/title.mp3`.

Write the full script to `{slug}_audio/narration_script.md` (one `## Scene NN` section per scene with the subsections above) so the user can review it in one place.

### Stage 4 — HARD GATE: review the narration script

Show the script and pause: **"Narration script ready — review before I generate audio. Each generation is billed (~$0.10/1k chars) and non-deterministic, so a bad script wastes credits. Reply `go` to generate, `edit` for changes, or paste a corrected version."**

Do NOT proceed without explicit approval. If the user wants changes: minor wording → update and re-show; "less excited / more intimate" → re-tag with the new direction; "redo scene X" → update just that scene.

### Stage 5: Generate audio (one MP3 per scene)

For each scene, call `mcp__elevenlabs__text_to_speech` with:
- `text` = the scene's `tagged` text (or `original` if not tagging)
- `voice_id` = chosen voice
- `model_id` = chosen model
- `stability` = `0.45`, `style` = `0.2`, `use_speaker_boost` = true (tune to taste)
- `output_directory` = `stories/{slug}/{slug}_audio/`

The MCP saves the file and returns its path. **Rename** the saved file to `{slug}_part_NN.mp3` (zero-padded scene index) — use the `Bash` tool (`mv`) so filenames match the locked convention. If a generation fails, capture the error and continue with the rest of the scenes — don't crash the batch.

**Leading-punctuation gotcha (Windows).** The MCP derives the saved filename from the first characters of the text, so if a scene's `text` begins with a quote (`"`) or other character invalid in a filename, the save fails with `[Errno 22] Invalid argument` even though the audio generated (and you're billed). Workaround: send that scene's text with the **leading** quote stripped — ElevenLabs doesn't voice quotation marks, so the spoken audio is identical. (Quotes *inside* the text are fine; only the first character matters for the filename.)

If you produced a title clip, generate it the same way and rename it to `title.mp3`.

After all scenes:
- Write `{slug}_audio/manifest.json` listing each clip: `index`, `filename`, `original`, `tagged` (if any), and the scene's `mood`/`scene` metadata. Include a `title_audio` entry if a title clip was made.
- Report: number of clips generated, approximate cost (total chars × $0.10/1k), any failures with the scene index for retry, and the audio folder path.

```json
{
  "story_slug": "the-little-cloud",
  "voice_id": "...",
  "model_id": "eleven_v3",
  "title_audio": { "filename": "title.mp3", "original": "The Little Cloud", "tagged": "[warmly] The Little Cloud." },
  "parts": [
    { "index": 1, "filename": "the-little-cloud_part_01.mp3", "original": "High in the sky...", "tagged": "[warmly] High in the sky...", "mood": "gentle, bright" }
  ]
}
```

### After Stage 5

The skill is done — one MP3 per scene plus a manifest, ready for the publisher. To redo specific scenes: "regenerate scenes X, Y" — generation is idempotent on filenames, so reruns overwrite cleanly. Or edit the script first and regenerate just those scenes.

## Cost expectations

ElevenLabs v3 is ~$0.10 per 1,000 characters. A short beginner story (~1,500–2,500 chars across all scenes) costs ~$0.15–$0.25 once. Audio tags add ~5–10% character overhead. Budget for 1–2 regenerations of some scenes since v3 is non-deterministic — the Stage 4 gate exists to get the script right *before* spending on audio.

## What this skill does NOT do

- Does not edit the story text — tags are added; the prose itself doesn't change.
- Does not generate music or sound effects — only narration.
- Does not do voice cloning — bring a `voice_id` from ElevenLabs' separate workflow.
- Does not QA the generated audio — listening and approval is the user's job.

## Compatibility notes

- Eleven v3 supports audio tags (`[warmly]`); `eleven_multilingual_v2` does not — match your tagging to the model.
- Eleven v3 does not reliably support SSML `<break>`; use `...` for pauses.
- v3 is non-deterministic — the same input can produce different audio across runs. The Stage 4 gate is the cost-control valve.
- Filenames MUST end up as `{slug}_part_NN.mp3` (and optionally `title.mp3`) so the publisher pairs audio with images by scene index.
