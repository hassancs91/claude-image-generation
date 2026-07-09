---
name: story-illustrator
description: Generates a consistent illustrated image for every scene of a story — keeping characters, locations, and visual style coherent across the whole sequence using cascading reference images. Reads a {slug}_scenes.json (from scene-splitter), proposes a visual style, ASKS the user for the aspect ratio and image model, extracts a visual bible, drafts a continuity-classified shot list, generates one reference image per character + location, then one image per scene (with a strict no-text/no-border constraint), and records every image in {slug}_images.json. Images are generated through the Fal API via the bundled fal_image.py script, with a pluggable model registry (nano-banana-2, nano-banana-pro, seedream-4, or any Fal model you add). Use this skill whenever the user wants to illustrate a story, generate scene images, draw the pictures for a storybook, build the illustrations, or produce a consistent visual sequence. Trigger on phrases like "illustrate this story", "generate the images", "draw the scenes", "make the pictures", "visualize this story", or whenever scenes.json exists and the user wants images. Requires a Fal API key (FAL_KEY in the environment or a .env file).
---

# Story Illustrator

Turns a story (already split into scenes) into a sequence of illustrations with **consistent characters, locations, and style** — using cascading reference images to preserve continuity from scene to scene.

This is where the storybook earns its polish. Naively prompting "scene 1", "scene 2", "scene 3" gives three different-looking children in three different rooms. This skill prevents that with a **bible → references → cascading scene images** workflow.

## When this skill applies

`{slug}_scenes.json` exists (from `scene-splitter`) and the user wants images. Also applies if the user pastes a story and asks to illustrate it — in that case, run `scene-splitter` first (or fall back to building a quick internal shot list).

The skill does NOT apply to:
- Single one-off image requests with no narrative (run `fal_image.py` directly, or call an image tool).
- Video/animation tasks.
- Cases where the user only wants the bible or shot list as text, not actual images.

## Required tools — the image backend

Images are generated through the **Fal API** using the bundled script [assets/fal_image.py](assets/fal_image.py). One call generates one image:

```bash
python .claude/skills/story-illustrator/assets/fal_image.py \
  --model nano-banana-2 --aspect 4:5 \
  --prompt "<full prompt>" \
  --ref <url> --ref <url> \
  --out stories/<slug>/<slug>_images/part_03.png
```

It submits to Fal, polls until done, **downloads the image locally**, and prints one JSON line: `{"url": "<fal cdn url>", "path": "<local file>", "model": "...", "cost_usd": 0.08}`. Capture **both** the `url` and the `path` (explained in Stage 5/6).

**Why a script, not an MCP:** the only thing this skill needs from an image generator is the primitive *(prompt, reference image URLs, aspect ratio) → an image*. A small stdlib script over the Fal HTTP API does exactly that with one dependency — a `FAL_KEY` — and keeps the model choice fully in your hands. (Narration, by contrast, uses the ElevenLabs **MCP** — the repo deliberately demonstrates both integration styles.)

**Before anything else**, confirm Fal is reachable:
```bash
python .claude/skills/story-illustrator/assets/fal_image.py --check
```
If it prints `{"fal_key": false}` (exit 1), stop and tell the user to set `FAL_KEY` (env var, or a `.env` at the repo root — see the README). Don't proceed without it.

## Model registry — and choosing a model (ASK each run)

Available models live in [assets/image-models.json](assets/image-models.json) — each entry maps a friendly key to its Fal endpoint, whether it accepts reference images (**required** for the cascade), how it encodes aspect ratio, and its cost per image. To add or swap a model, edit that file — no code change. The bundled defaults:

| Key | Model | Cost/img | Best for |
|---|---|---|---|
| `nano-banana-2` | Nano Banana 2 (Google) | $0.08 | references + single-character scenes |
| `nano-banana-pro` | Nano Banana Pro (Gemini 3 Pro Image) | $0.15 | multi-character beats, fine detail |
| `seedream-4` | Seedream v4 (ByteDance) | $0.03 | cheapest; a different look / testing |

**Picking the model is a HARD GATE — ask the user each run** (Stage 1). Read the live prices from `image-models.json` and offer:

1. **`nano-banana-2`** — fast & cheap, everywhere.
2. **`nano-banana-pro`** — best quality, everywhere.
3. **Smart mix** *(suggested)* — `nano-banana-pro` for scenes with **2+ characters in frame**, `nano-banana-2` for everything else **and** all reference plates. Best value: pay for the pro model only where multiple characters must stay coherent.
4. **`seedream-4`** (or any other registry key) — cheapest / alternative style.

Whatever they pick, **references always use the cheapest reference-capable model** (`references_model` in the registry, default `nano-banana-2`) unless the user chose "pro everywhere." If the orchestrator pre-supplied a model choice, honor it and skip the prompt.

## Workflow — six stages (plus optional Stage 4.5 QA)

A **Stage 4.5 vision-QA pass** is available between scene generation and finishing. It is **opt-in** (default OFF) — invoke with `qa`, `--qa`, or "with QA". It reviews the generated images and produces a suggestion table; it never auto-regenerates.

### Stage 0: Load scenes.json

Read `{slug}_scenes.json` from `stories/{slug}/`. Each scene becomes exactly one image:
- one image per scene, in order, indexed to match `scenes[i].index`
- `panel_type` drives framing (`establishing` → wide; `action` → dynamic; `reaction` → close on face; `detail` → tight on object) — don't override it; that variety is what makes the gallery feel like a real book
- `dominant_action` becomes the prompt body
- `characters` selects which character references to attach
- `scene` selects the location reference
- `mood` informs lighting/color tone
- output image is recorded as scene index `NN` so the publisher can pair it with `{slug}_part_NN.mp3`

If no `scenes.json` exists, ask the user to run `scene-splitter` first.

### Stage 1: Connect and orient

1. Confirm Fal is reachable: run `python .claude/skills/story-illustrator/assets/fal_image.py --check`. If `fal_key` is false, stop and tell the user to set `FAL_KEY` (env var or `.env` at the repo root). Don't continue without it.
2. Propose ONE visual style based on the story's tone and audience — don't list five options. For beginner children's stories, a strong default is **"warm, soft watercolor children's-book illustration, gentle rounded shapes, cozy lighting."** The user can override.
3. **Determine the aspect ratio — HARD GATE, ask; do not pick silently.** If the orchestrator pre-supplied one (look for "Aspect ratio: `4:5`"), use that and skip the prompt. Otherwise ask:
   > "What aspect ratio? Common options: `4:5` portrait (storybook / phone, the default for picture books), `1:1` square, `3:4` portrait (book page), `16:9` widescreen. Pick one."
   Lock the answer for the whole run — it MUST be passed to every image call so the storybook is visually consistent.
4. **Determine the image model — HARD GATE, ask; do not pick silently** (it spends money). Read the model keys + live prices from [assets/image-models.json](assets/image-models.json) and present the four options from the *Model registry* section above (nano-banana-2 / nano-banana-pro / **Smart mix** *(suggested)* / seedream-4 or other). If the orchestrator pre-supplied a model, honor it and skip. Record the chosen **policy** (single model, or smart-mix) — Stage 5 applies it per scene.
5. State the scope with a real dollar estimate from the chosen model(s): "Style: [proposed]. Aspect: [answer]. Model: [choice]. N scenes + ~M references ≈ **$X.XX** (refs at $a, scenes at $b). Reply `go` to proceed."

### Stage 2: Build the visual bible

Read [references/bible-extraction.md](references/bible-extraction.md) for the full process. Briefly: extract a Markdown bible covering **cast** (each recurring character's physical traits, clothing, distinguishing details, default expression), **locations** (each recurring place's key features + mood), **recurring props**, and the locked **style sheet**. Run the two-pass extraction (extract, then re-read the story to catch missed characters/locations) — don't skip the second pass.

For anything the story doesn't physically describe, **invent specific, distinctive details** and record them. Specifics (exact clothing colors, hair style, a named accessory) are what make consistency *visible* across scenes; vague descriptions drift.

Two special tables when relevant:
- **Prop-state tracker** — if a key object visibly changes across scenes (a balloon inflating, a cup filling, a flower wilting then reviving), enumerate its state per scene. Otherwise the model defaults to the "neutral" version of the prop in every scene. Skip only if nothing changes state.
- **Characters-in-frame map** — for stories with ≥3 named characters, list who must be VISIBLE in each scene (separate from who merely *exists*). Without it, close shots silently drop characters who should be in the background.

**Editorial check (child-safe):** verify each character's design is modest and child-appropriate (shoulders/torso covered, sensible everyday clothing, no suggestive posing) *before* approving — fixing it after references are generated costs a regeneration per affected image. See CLAUDE.md → Editorial standards.

Write the bible to `{slug}_bible.md` and pause: "Bible drafted — anything to change before I generate references?" (The user can edit the file directly or say `go`.)

### Stage 3: Generate reference images

Generate one reference image per **consistent character** and per **recurring location**, using the references model (`references_model` in the registry — default `nano-banana-2`). Each is a single `fal_image.py` call with **no `--ref`** (references are generated from the prompt alone), saved under `stories/<slug>/<slug>_images/`:

```bash
python .claude/skills/story-illustrator/assets/fal_image.py \
  --model nano-banana-2 --aspect <locked> \
  --prompt "<style> <character/location description> <no-text + no-border>" \
  --out stories/<slug>/<slug>_images/ref_pip.png
```

**Universal prompt rules — in EVERY reference AND scene prompt:**

> **No text, no labels, no signs, no readable writing in the image. No book titles, no name tags, no words on walls.**
>
> **No borders, no frames, no decorative edges, no inner margins, no paper-edge effects, no vignettes. Full-bleed illustration — the art extends to all four canvas edges.**

Both are non-negotiable. The no-text rule exists because image models hallucinate gibberish text into illustrations whenever there's a book, sign, or wall. The no-border rule keeps the gallery consistent (some models render scenes as matted "pages" otherwise). **Prefer positive phrasing** of the desired end-state ("a purely pictorial illustration with clean, unmarked surfaces; the art bleeds fully to all four edges") plus a short affirmative no-text clause — that outperforms a long wall of "no X" negations. Keep the explicit negation block for genuinely text-prone scenes (books, signs, walls with writing).

Reference prompts must:
- Include the locked style descriptor verbatim
- Include the no-text + no-border rules
- Describe the character or location in detail (pull from the bible)
- **Characters:** full body, neutral pose, neutral expression, plain white background extending to all edges (no inner frame around the figure)
- **Locations:** wide-angle plate, no people, all key features visible, neutral lighting, full-bleed

**One reference per character — do NOT combine characters into a group portrait**, even to save a generation. A group ref locks them into group-portrait poses; when a scene needs them re-posed (seated, reaching, bending), the model invents poses without per-character anchors and drops characters. Solo ref per character. Locations may bundle (an empty room is fine) since they aren't posed.

**Do NOT generate a "style anchor" hero image** — style is carried by the character refs + location refs + the style descriptor in every prompt; a style anchor with scene content causes duplication artifacts downstream.

After each generation, capture the printed `url` **and** `path` and store them in `{slug}_images.json` under `references` (see schema in Stage 6). Pause: "References generated — quick review, proceed to scenes?" Show the local files (and/or URLs).

### Stage 4: Draft the shot list

Read [references/shot-list.md](references/shot-list.md) for continuity rules and the prompt schema. Build one shot per scene from `scenes.json`, classifying each by continuity:

- **HARD CUT** — new location, time skip, or scene 1. Refs: characters + location + style. **No previous-scene ref.**
- **SOFT CUT** — same place/time, next moment. Refs: characters + location + **previous scene image** + style. The previous-scene ref carries clothes/hair/mood/lighting forward — this is the core consistency mechanism.
- **MICRO CUT** — same moment, tiny change. Refs: previous scene image (dominant) + characters + style.
- **STATE RESET** — same scene context BUT the character's physical state explicitly changed (got wet, changed clothes, got hurt). **Drop the previous-scene ref** (it would carry the old state); use character + location refs only and describe the new state in prose.

Derive the classification by comparing each scene to the previous one (location/time/state fields). Write the shot list to `{slug}_shotlist.md`: per scene → type/angle, action (the moment, in prose), location, characters present, continuity class, state-reset flag, refs to use, and any framing/lighting notes. **Keep prompts about the moment and the change — do NOT redescribe characters or settings the references already carry.**

**If the user chose Smart mix**, also record a `model` per scene in the shot list: count the characters that must be **visible in frame** (use the characters-in-frame map when present, else the scene's `characters`). 2+ visible → `nano-banana-pro`; otherwise → `nano-banana-2`. List which scenes get the pro model so the cost is transparent. (For a single-model choice, every scene uses that one model.)

Show the shot list with a **dollar** estimate from the per-scene models. Gate: "N scenes ≈ $X.XX ([k] at pro, [n] at the base model). Reply `go` to generate, or `review` to inspect first."

### Stage 5: Generate scene images with cascading references

For each scene in order:

1. Build the full prompt: **style descriptor + no-text + no-border constraints + the scene's prompt body.**
2. Paste in the **prop-state line** and the **characters-in-frame roster** from the bible (when those tables exist).
3. Apply the targeted anti-failure clauses from [references/shot-list.md](references/shot-list.md) as needed:
   - **Anti-duplicate-environment** — for a close shot of an object that also exists in the room (a table close-up in a kitchen), add "ONE [object] only — no second [object] in the background."
   - **Anatomy budget** — for body-part close-ups, state the exact count and single source ("TWO hands, both the mother's; no extra limbs").
   - **No floating text on question/thought scenes** — describe the physical motion ("hands open, palms up, eyebrows raised") rather than "questioningly", and add "no thought bubbles, no question marks, no floating text."
   - **Solo-close scenes stay solo** — if the scene's `characters` list is one name and the framing is close, render just that character; don't add others "in the background" (the model renders them at separate tables/seats).
4. Assemble the reference URL list per the scene's continuity class, in priority order: **characters first, then location, then previous scene.** Respect the model's **`max_refs`** (nano-banana models cap at **4**; seedream allows more). When a SOFT-cut scene would exceed the cap (3 characters + location + previous = 5), **drop the standalone location ref** — the previous-scene image already carries the location. Use the references' **`url`** values (the Fal CDN URLs) and, for the previous-scene ref, the **`url`** returned for that scene earlier in this run.
5. Call the backend with this scene's model (from the Stage 4 policy — the smart-mix `model`, or the single chosen model) and the locked aspect ratio:
   ```bash
   python .claude/skills/story-illustrator/assets/fal_image.py \
     --model <scene model> --aspect <locked> \
     --prompt "<full prompt>" \
     --ref <char url> --ref <location url> --ref <previous scene url> \
     --out stories/<slug>/<slug>_images/part_<NN>.png
   ```
6. Capture the printed `url` **and** `path` into `{slug}_images.json` under `shots` at this scene's index (`index` = `NN`, zero-padded to match `{slug}_part_NN.mp3`).
7. The next SOFT/MICRO scene uses **this scene's `url`** as its previous-scene reference (the cascade). The `path` is the durable local copy the publisher embeds.

On failure, read the script's error message and act: a non-zero exit prints the reason. `auth`/`FAL_KEY` → stop, tell the user to fix the key; `429` rate-limit/out-of-credits → stop and tell the user; `422` validation → check the params/refs and retry; a timeout → retry once; a Fal `safety` block → surface to the user and suggest rephrasing the prompt. Don't silently skip a scene — every scene needs an image for the publisher to pair it.

Don't run vision-QA inline per scene — it adds latency. QA (if requested) happens after all scenes in Stage 4.5.

### Stage 4.5 (OPT-IN): Vision QA — suggestion only

**Trigger:** the user asked for QA. Default OFF.

**Hard rule: never auto-regenerate.** Produce a suggestion table; the human decides what to redo.

1. The scene images are already saved locally (each shot's `path` in `{slug}_images.json`) — no download needed.
2. Read each `path` with the `Read` tool (Claude is multimodal — reading the image loads it into vision context). Read them in parallel in one message.
3. For each image, check against the bible + scene metadata: does each visible character match their locked design? Is the required prop present and in the right state? Does lighting match the mood? Does the composition match the `panel_type`? Any hallucinated text/labels/borders? Any anatomy issues (hand count, doubled limbs), extra characters, or duplicated objects?
4. Compile one table: scene # · findings · severity (🟢 OK / 🟡 minor / 🔴 worth a redo). List the 🔴 items at the top.
5. Prompt with explicit, named options (no auto-fix): `regen N` (with a delta), `regen N M ...`, `keep`, `regen all warns`.
6. Run approved regens per [references/qa-and-retry.md](references/qa-and-retry.md) (re-run `fal_image.py` for that scene, overwriting its `part_NN.png`), update its `url` + `path` in `{slug}_images.json`, optionally re-QA those scenes, loop until `keep`.

### Stage 6: Finalize the registry

Ensure `{slug}_images.json` is complete and present it to the user:

```json
{
  "story_slug": "the-little-cloud",
  "style": "warm soft watercolor children's-book illustration",
  "aspect_ratio": "4:5",
  "references": [
    { "name": "pip", "kind": "character", "path": "stories/the-little-cloud/the-little-cloud_images/ref_pip.png", "url": "https://v3.fal.media/...", "model": "nano-banana-2" },
    { "name": "sky", "kind": "location",  "path": "stories/the-little-cloud/the-little-cloud_images/ref_sky.png", "url": "https://v3.fal.media/...", "model": "nano-banana-2" }
  ],
  "shots": [
    { "index": 1, "path": "stories/the-little-cloud/the-little-cloud_images/part_01.png", "url": "https://v3.fal.media/...", "model": "nano-banana-2",   "continuity": "HARD CUT" },
    { "index": 2, "path": "stories/the-little-cloud/the-little-cloud_images/part_02.png", "url": "https://v3.fal.media/...", "model": "nano-banana-pro", "continuity": "SOFT CUT" }
  ]
}
```

Each entry carries both `path` (durable local file) and `url` (the Fal CDN URL, used as a cascade reference during the run). `shots[i].index` MUST match `scenes[i].index`. The publisher prefers `path` (it embeds the local file, so a stale Fal URL never breaks the storybook).

Confirm: "Wrote `{slug}_images.json` — N scene images + M references. Ready for the publisher." Optionally offer to build a quick local gallery for review; the publisher's final storybook is the real review surface.

## Triggering retries

When the user flags an image, read [references/qa-and-retry.md](references/qa-and-retry.md): translate the feedback into specific corrective deltas, regenerate by re-running `fal_image.py` with **the previous image's `url` as the primary `--ref`** (so the model treats it as "mostly right, fix these things"), overwrite `part_NN.png`, replace the `url` + `path` in `{slug}_images.json`, and re-present.

## What good looks like

- `{slug}_bible.md` — a bible the user can read and trust
- `{slug}_shotlist.md` — the shot list with continuity classes
- `{slug}_images.json` — every reference + scene image (`path` + `url` + `model`), indexed
- 2–5 reference plates + 8–12 scene images saved under `stories/{slug}/{slug}_images/`
- A natural flow: user approves the bible, says `go` a couple times, has all images a few minutes later

## Reference files

- [references/bible-extraction.md](references/bible-extraction.md) — two-pass bible extraction
- [references/shot-list.md](references/shot-list.md) — continuity classification + prompt schema
- [references/qa-and-retry.md](references/qa-and-retry.md) — corrective-delta retry pattern
- [references/image-backends.md](references/image-backends.md) — the model registry + adding/swapping Fal models
- [assets/fal_image.py](assets/fal_image.py) — the Fal image script (stdlib only)
- [assets/image-models.json](assets/image-models.json) — the model registry
