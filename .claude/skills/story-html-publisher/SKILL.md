---
name: story-html-publisher
description: Final step of the AI Storybook pipeline. Consolidates the scenes, images, and per-scene audio into ONE self-contained HTML storybook — a swipe/tap player with every image and audio clip embedded as base64 so the single file works offline and can be shared as-is. Reads {slug}_scenes.json, {slug}_images.json, and {slug}_audio/, then writes {slug}_story.json and {slug}.html. Use this skill whenever the user wants to build the final storybook, export to HTML, package the story, make the storybook file, generate the HTML, or wrap up the pipeline. Trigger on phrases like "build the storybook HTML", "export to HTML", "make the final file", "package the storybook", "generate the storybook", "wrap up the pipeline", or whenever the scenes + images + audio all exist and the user wants the single shareable file. Produces a single self-contained .html (images + audio embedded).
---

# Story HTML Publisher

Takes everything the upstream skills produced and emits **one self-contained HTML storybook**: a swipe/tap player where each scene is one screen (illustration + narration text), with the playback controls in a fixed footer. It opens with a **dedicated cover page** — the first illustration shown clean, playing only the short spoken title. Every image and audio clip is embedded as a base64 data URI, so the single `.html` file works offline, opens with a double-click, and can be emailed or dropped on any static host with no assets folder.

This skill does **no creative work** — no new text, images, or audio. It only reads, validates, pairs, embeds, and writes. If something is missing upstream, it reports the gap rather than fabricating.

## When this skill applies

The pipeline's earlier skills have run and the user wants the final output: "build the storybook", "export to HTML", "make the final file", "wrap up the pipeline".

Does NOT apply to stories that haven't been through `scene-splitter` + `story-illustrator` + `story-narrator` — point the user to the missing step.

## Required inputs

In `stories/{slug}/`:

| Artifact | Producer | Path |
|---|---|---|
| Scenes spine | scene-splitter | `{slug}_scenes.json` |
| Image registry | story-illustrator | `{slug}_images.json` |
| Audio clips | story-narrator | `{slug}_audio/{slug}_part_NN.mp3` |
| Title clip (optional) | story-narrator | `{slug}_audio/title.mp3` |

Everything pairs by **scene index**: `scenes[i].index = N` → image from `images.json.shots[]` where `index = N` → audio `{slug}_part_NN.mp3`.

## Workflow — four stages with one hard gate

### Stage 1: Discover and validate

1. Determine the `slug` (user argument → the `*_scenes.json` in the working dir → ask).
2. Locate the three inputs. Confirm each scene has both an image (in `images.json`) and an audio file. Build a pairing table: index → text snippet → image present? → audio present?
3. **Reconstruction sanity check:** the scene count in `scenes.json` should match the number of `shots` in `images.json` and the number of `_part_NN.mp3` files.
4. Report findings:
   > Found 9 scenes, 9 images, 9 audio clips (+ title clip). All paired. Ready to build.
   If anything is missing, list the gaps. Don't proceed to build with gaps unless the user says "build partial" (the build script will embed what exists and leave placeholders for the rest).

### Stage 2: Build the HTML

Run the build script (preferred):

```bash
python .claude/skills/story-html-publisher/assets/build_html.py {slug}
```

It downloads/reads every image and audio file, embeds them as data URIs, injects them into [assets/player-template.html](assets/player-template.html), and writes `stories/{slug}/{slug}_story.json` + `stories/{slug}/{slug}.html`. Read [references/build-html.md](references/build-html.md) for what it does, options, and how to do it by hand if the script can't run.

On Windows use `python`; on macOS/Linux use `python3`. Stdlib only — no installs needed.

### Stage 3 — HARD GATE: review the storybook

Report:
1. Output path: `stories/{slug}/{slug}.html`, its size (MB), and scene count
2. Any warnings the build emitted (missing image/audio for a scene)
3. A one-liner: **"Open `stories/{slug}/{slug}.html` in your browser to read the finished storybook."**

Then prompt:

> **Storybook built — open it and review, then reply:**
> - `done` to finish
> - `rebuild` to regenerate the HTML (e.g. after swapping an image/audio file)
> - `fix image N` / `fix audio N` — if a scene's media is wrong, regenerate it upstream (illustrator/narrator), then `rebuild`

This is the final review surface — the user reads the actual storybook here. Don't declare success before they've had the chance to open it.

> ⚠️ The `.html` can be large (several MB) because media is embedded. It opens fine in a browser but may be slow to preview inside a chat/artifact viewer — tell the user to open it locally in a real browser.

### Stage 4: Finish

On `done`, confirm in one line: "Storybook ready: `stories/{slug}/{slug}.html` ({N} scenes, {size} MB). Fully self-contained — share or host it anywhere."

## What the finished storybook does

- A dedicated cover page (slide 0): the first illustration shown clean — no overlaid title text, no scrim, no glyph — with the title in the header. It plays the optional spoken title clip, then auto-advances into scene 1.
- One scene per screen after that: illustration + narration text, controls in a fixed footer
- Tap the image (or the footer play button) to play/pause the scene's narration. No play glyph is drawn on the image.
- Swipe (left = next, right = prev), arrow keys, on-screen buttons, or tap a progress dot to navigate
- Auto-play toggle: when a scene's narration ends, advance to the next scene. Every slide is uniform (one image, one clip, advance on `ended`) — no title→body audio chaining
- A "The End" screen with a "Read again" button at the finish
- Serif body text matching the serif title, LTR English, warm storybook styling, responsive (phone + desktop), no external dependencies

## What this skill does NOT do

- Does NOT generate new content (text/images/audio) — it only packages.
- Does NOT upload anywhere — local file output only. (The result is portable; the user can host it wherever.)
- Does NOT modify upstream artifacts.
- Does NOT support multiple stories per run — one story per invocation.

## Reference files

- [references/build-html.md](references/build-html.md) — what the build does, options, the data shape, and the by-hand fallback
- [assets/build_html.py](assets/build_html.py) — the build script (stdlib only)
- [assets/player-template.html](assets/player-template.html) — the self-contained swipe player template
