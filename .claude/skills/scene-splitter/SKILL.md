---
name: scene-splitter
description: Splits a plain English story into a numbered list of SCENES — each scene being one moment that gets exactly one illustration AND one narration clip downstream. The first step of the AI Storybook pipeline. Tuned for beginner-level stories (short sentences, ~8-12 scenes), with a per-scene length cap so each scene fits one phone screen without scrolling. Use this skill whenever the user wants to split a story into scenes, prepare a story for the storybook pipeline, break a story into pages/panels, or produce a scenes spine for the illustrator and narrator. Trigger on phrases like "split this story into scenes", "break this into pages", "prepare this story for the storybook", "make scenes for illustration", or whenever the user provides an English story and wants it chunked for a picture-book pipeline. Outputs a {slug}_scenes.json file consumed by the story-illustrator and story-narrator so they produce aligned output (1 image + 1 audio per scene).
---

# Scene Splitter

Takes a plain English story and produces a numbered list of **scenes** — each scene being one moment that gets exactly one illustration and one narration clip downstream.

This is the upstream spine of the AI Storybook pipeline. Splitting once here and feeding both the illustrator and the narrator from the same `{slug}_scenes.json` keeps everything in lockstep: **image N pairs with audio N pairs with paragraph N.** No drift, no negotiation between skills.

## When this skill applies

The user has an English story and wants to prepare it for the illustration + narration pipeline. Common phrasings: "split this into scenes", "break this into pages", "prepare this story for the storybook", "make scenes for illustration".

The skill does NOT apply to:
- Stories that need only narration OR only images standalone (the illustrator and narrator can split on their own when used independently)
- Non-narrative content (essays, instructions, lists)

## Architectural rule: one scene = one moment = one image = one narration clip

A scene is a single moment that fits one illustration. Operationally, a new scene starts at any of:

- **Action transition** — a different action happens
- **Scene change** — a different location or a significant time jump
- **Emotional turn** — joy → fear, calm → urgency, doubt → resolve
- **Character entry/exit** — someone new appears or leaves the moment
- **Dialogue beat** — a meaningful line of speech that deserves its own picture

Scenes are deliberately short and many. The storybook player renders **one scene at a time**, and the text MUST fit on a phone screen without scrolling. That drives the hard length cap below.

## Reading level + length cap (beginner default)

This pipeline targets **beginner** readers. The cap is screen-fit-driven, not API-driven:

| Level | Per-scene hard cap | Target scene count |
|---|---|---|
| **beginner** (default) | **240 characters** | 8–12 scenes |

The cap is the number of characters in a single scene's `text`. Keep most scenes well under it (~120–180 chars reads best on a phone). To scale this pipeline up for longer/harder stories, raise the cap and the target count here — nothing downstream needs to change.

## Workflow — five stages with one hard gate

### Stage 1: Story analysis

1. Read the full story.
2. Detect: total character count, named characters, distinct scenes/locations, rough emotional arc.
3. **Determine the slug** from the title (line 1) or filename — lowercased, hyphenated, ASCII-safe (`^[a-z0-9-]+$`, max 60 chars). Examples: "The Little Cloud" → `the-little-cloud`; `red_balloon.md` → `red-balloon`.
4. Estimate scene count (aim for the 8–12 beginner range; more for a longer story).
5. Output a one-line summary: "Story is [N] chars, [X] characters, [Y] locations, ~[Z] scenes expected at beginner level. Slug: `{slug}`."

### Stage 2: Scene identification

Walk the story in order. At each candidate boundary, decide: new scene or extend the current one? Use the boundary rules above. **When unsure, prefer MORE scenes** — it's easier to merge two at the gate than to retroactively split one.

For each scene, capture the **exact text** from the source. The splitter chooses BOUNDARIES, not content — do not reword, summarize, or rewrite the author's prose. (If a sentence must be trimmed to fit the cap, that's an author decision — surface it at the gate, don't silently edit.)

### Stage 3: Per-scene metadata

For each scene, populate:

- `index` — 1-based
- `role` — `cover` for scene 1, `closing` for the last scene, `body` for everything else
- `panel_type` — one of `establishing` | `action` | `reaction` | `detail` (drives framing variety downstream):
  - `establishing` — wide, sets the place. Good for scene 1 and any location change.
  - `action` — something is happening; dynamic composition.
  - `reaction` — close on a character's face/feeling.
  - `detail` — tight on one object or element.
- `text` — the exact story text for this scene (no title prefix on scene 1 — see below)
- `char_count` — character count of `text`
- `scene` — location/setting in 2–4 words (e.g. "sunny meadow", "cozy kitchen")
- `characters` — array of named characters present in this moment
- `mood` — emotional tone in 1–3 words (e.g. "warm, curious")
- `dominant_action` — what happens in this moment, in one sentence (the illustrator turns this into the image prompt)

**Title handling for the cover scene (LOCKED).** The story's title (the `# Heading` on line 1) MUST NOT appear in `scenes[0].text`. The player shows the title in the header and builds a dedicated cover page from the first illustration (with the spoken title clip); scene 1's `text` then renders as its own story page. If the title were left in `scenes[0].text` it would show up twice (header + as scene 1's paragraph). Strip it from scene 1's `text` and store it at the top level instead:

```json
{
  "story_slug": "the-little-cloud",
  "story_title": "The Little Cloud",
  "target_level": "beginner",
  "language": "en",
  "total_scenes": 9,
  "scenes": [
    {
      "index": 1,
      "role": "cover",
      "panel_type": "establishing",
      "text": "High in the sky lived a little cloud named Pip.",
      "char_count": 47,
      "scene": "wide blue sky",
      "characters": ["Pip"],
      "mood": "gentle, bright",
      "dominant_action": "A small white cloud drifts alone in a big blue sky."
    }
  ]
}
```

### Stage 3.5: Validation (reconstruction + length cap)

**Reconstruction check.** Concatenate `story_title + "\n\n" + scenes[*].text` (single spaces between scenes) and verify it reconstructs the original story. The title goes at the front because it was stripped from `scenes[0].text`. If even one word is missing or duplicated, abort and report which boundary is broken — do NOT proceed to the gate with broken reconstruction.

**Length-cap check.** For every scene, verify `char_count` ≤ 240. If any scene is over cap:
1. Do NOT show the gate yet.
2. List the over-cap scenes (index, char_count, first ~80 chars).
3. Re-enter Stage 2 for those scenes: find an internal boundary (action shift, emotional turn, dialogue handoff) and split. If a scene is one indivisible moment but still over cap, flag it `OVERSIZED — needs author trim` rather than force-splitting on a non-boundary.
4. Re-run the reconstruction check, then proceed.

### Stage 4 — HARD GATE: review scenes

Show the user the proposed scene list in a compact table (so 10+ scenes fit on screen). Columns: index · role · panel_type · mood · char_count · first ~60 chars + ellipsis · dominant_action.

Below the table, prompt:

> **Scene plan ready — review and approve before I write scenes.json. Reply:**
> - `go` to commit
> - `merge N M` to combine two adjacent scenes
> - `split N` to split a scene further (I'll propose where)
> - `edit N` to fix one scene's metadata
> - `fix N <reason>` for free-form feedback (e.g. `fix 7 too long, split before "but then"`)
> - `redo` to restart with a different approach

If the user issues a change, apply it, re-run Stage 3.5 validation, and re-show the gate. Loop until `go`.

This gate is where human taste enters: it costs nothing now, but a wrong boundary means a wrong image AND a wrong audio clip downstream.

### Stage 5: Output

Write `{slug}_scenes.json` to the working directory `stories/{slug}/`. Confirm in one line: "Wrote `{slug}_scenes.json` — N scenes, ready for the illustrator and narrator."

## What this skill does NOT do

- Does not edit or rewrite story text — only chooses boundaries.
- Does not generate audio or images — those are downstream skills.
- Does not classify or tag the story (this beginner pipeline skips classification by design).
- Does not write to any database or upload anything — local file output only.

## Compatibility notes

- Output is consumed by `story-illustrator` and `story-narrator`. Both accept `{slug}_scenes.json` and skip their own splitting, so the image for scene N and the audio for scene N stay aligned by index.
- Image filenames downstream are `{slug}_part_NN.png`; audio filenames are `{slug}_part_NN.mp3`, where `NN` is the zero-padded scene index. The publisher pairs them by that index.
- Be conservative: when in doubt, more scenes. The user can `merge` at the gate.
