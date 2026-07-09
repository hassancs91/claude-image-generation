---
name: storybook-pipeline
description: Orchestrator that runs the full AI Storybook pipeline end-to-end on one English story. Dispatches the 4 component skills in order — scene-splitter → story-illustrator → story-narrator → story-html-publisher — using the locked filename convention {slug}_* and {slug}_part_NN.{png,mp3} so every image and audio clip pairs by scene index, ending with one self-contained HTML storybook. Use this skill whenever the user wants to run the pipeline, make a storybook from a story, turn a story into an illustrated narrated storybook, process a story end to end, or build the storybook without invoking each skill by hand. Trigger on phrases like "run the pipeline on stories/my-story.md", "make a storybook from this", "turn this into a storybook", "build the storybook end to end", "process this story", or whenever the user drops an English story in stories/ and wants the full split → illustrate → narrate → HTML flow. Preserves every sub-skill's hard gate. Optionally accepts "with QA" to enable the illustrator's vision-QA pass.
---

# Storybook Pipeline (Orchestrator)

The **runbook** for turning one English story into a finished, self-contained HTML storybook. It does no creative work itself — it dispatches the 4 component skills in order, with the right artifact paths, and locks the filename convention so every output pairs cleanly by scene index.

It exists so that in a fresh session, "make a storybook from this story" has a single entry point — no need to remember the 4 skills, their order, or the filename conventions.

## When this skill applies

The user has an English story (typically in `stories/`) and wants the full output: scenes + images + audio + a single HTML storybook. Common phrasings:
- "run the pipeline on `stories/the-little-cloud.md`"
- "make a storybook from this story"
- "turn this into an illustrated storybook"
- "build the storybook end to end"

Does NOT apply to:
- **Single-step requests** — if they only want images, invoke `story-illustrator`; only audio, `story-narrator`. The orchestrator is for the full chain.
- **Re-running after partial completion** — if some artifacts exist, detect them and resume from the next missing step; don't blindly overwrite. Ask if unsure.

## Pipeline order (LOCKED)

```
input:  stories/{slug}.md
1. scene-splitter         → {slug}_scenes.json
2. story-illustrator      → {slug}_bible.md, {slug}_shotlist.md, {slug}_images.json
3. story-narrator         → {slug}_audio/{slug}_part_NN.mp3 (+ manifest.json, optional title.mp3)
4. story-html-publisher   → {slug}_story.json + {slug}.html   ← the deliverable
```

Steps 2 and 3 both read `{slug}_scenes.json` and are independent — but in an interactive session run them in order so the user reviews each at its own gate.

## Slug + filename convention (LOCKED)

The slug is derived from the story title or filename: lowercased, hyphenated, ASCII-safe (`^[a-z0-9-]+$`, max 60 chars). Every artifact shares it. All artifacts live in `stories/{slug}/`; the raw `.md` stays at `stories/` (it's the trigger, not an artifact). See [CLAUDE.md](../../../CLAUDE.md) for the full filename table.

## Workflow — five dispatch stages

### Stage 0: Intake

1. **Identify the story file** (explicit argument → the single new `*.md` in `stories/` → ask).
2. **Determine the slug.** Read line 1 (the `# Title`) + the filename; propose a slug. One-line confirm: "Slug: `the-little-cloud`. OK?" — proceed on `go`. *(HARD GATE — locks the slug into every artifact.)*
3. **Create the working dir** `stories/{slug}/`. All sub-skills output there.
4. **Detect completed stages.** Glob for `stories/{slug}/{slug}_scenes.json`, `_images.json`, etc. If any exist, list them and ask: skip those stages or redo? Default = skip completed.
5. **Check for the QA flag.** If the user said "with QA" / "--qa", note `qa_enabled = true` for the illustrator. Default OFF.
6. **Ask the image aspect ratio AND model up front — HARD GATES.** Don't wait until Stage 2; settle both now so the long stages run uninterrupted:
   > "What aspect ratio? `4:5` portrait (storybook / phone — the default), `1:1` square, `3:4` book page, or `16:9` widescreen."
   > "Which image model? `nano-banana-2` (fast & cheap, ~$0.08/img), `nano-banana-pro` (best for multi-character, ~$0.15/img), **Smart mix** (pro only for multi-character beats — suggested), or `seedream-4` (cheapest, ~$0.03/img). See `image-models.json`."
   Lock them as `aspect_ratio` and the model choice and pass both to the illustrator at Stage 2. **Ask — do not infer.** Aspect ratio locks into every image; both gates spend money. They pause even under an auto-mode reminder.
7. **Pre-flight checks:** `stories/` is writable; `FAL_KEY` is resolvable (`python .claude/skills/story-illustrator/assets/fal_image.py --check` — re-checked at Stage 2); the ElevenLabs MCP is connected (re-checked at Stage 3); and the user has (or will provide) an ElevenLabs `voice_id` for the narrator.

### Stage 1: Dispatch scene-splitter

Invoke `scene-splitter` with the story path, the slug, and output dir `stories/{slug}/`. The user approves the scene plan at its hard gate. Output: `{slug}_scenes.json` — the spine for stages 2 + 3.

### Stage 2: Dispatch story-illustrator

Invoke `story-illustrator` with:
- `stories/{slug}/{slug}_scenes.json` and the slug
- A style hint from the story's tone (e.g. "warm soft watercolor children's-book illustration" for a gentle beginner story)
- **Pre-locked aspect ratio + model** from Stage 0: "Aspect ratio: `{aspect_ratio}` (already chosen, do not re-ask). Image model: `{model choice}` (already chosen, do not re-ask)."
- If `qa_enabled`, add "with QA"
- A note: "Generate one image per scene, indexed to match `scenes.json`. Save `{slug}_bible.md`, `{slug}_shotlist.md`, `{slug}_images.json` to `stories/{slug}/`."

The illustrator's own aspect-ratio and model prompts are skipped because the orchestrator pre-supplied both. The user approves the **bible** (Stage 2 gate — remind them to verify child-safe character designs *before* approving, since fixing after generation costs a regen per image), the **references**, and the **shot list / images**. Each image costs money (Fal) — these are hard gates.

### Stage 3: Dispatch story-narrator

Invoke `story-narrator` with:
- `stories/{slug}/{slug}_scenes.json` and the slug
- A note: "One MP3 per scene, saved as `{slug}_part_NN.mp3` in `stories/{slug}/{slug}_audio/`. Detect `scenes.json` and skip your own splitting."
- The ElevenLabs `voice_id` if known (else the narrator asks once)

The user approves the narration script at the narrator's hard gate (each TTS call is billed). Output: `{slug}_audio/` with N MP3s + manifest.

### Stage 4: Dispatch story-html-publisher

Invoke `story-html-publisher` with the slug. It discovers the artifacts automatically, runs the build script, and writes `{slug}_story.json` + `{slug}.html`. The user reviews the finished storybook at its hard gate and replies `done`.

### Stage 5: Final summary

One-screen summary:
- Artifacts produced (with paths) — ending with the headline: **`stories/{slug}/{slug}.html`**
- Total cost: Fal images (~$X, from the per-scene models) + ElevenLabs narration
- "Open `stories/{slug}/{slug}.html` in your browser to read the finished storybook."

## Gates — preserved, not bypassed

This orchestrator does NOT auto-approve gates. **Gates pause regardless of any auto-mode / "work without stopping" reminder** — that reminder applies to read-only work, not to gates that spend money or commit a creative choice.

| Skill | Gate | Why preserve |
|---|---|---|
| (orchestrator) | slug + aspect ratio + image model | Lock into every artifact / every image; the model spends money |
| scene-splitter | scene plan | Wrong boundaries → wrong image AND wrong audio |
| story-illustrator | bible, references, shot list/images (+QA) | Each image costs money (Fal); bad bible → bad images; child-safe check |
| story-narrator | narration script | Each TTS call is billed; bad script wastes credits |
| story-html-publisher | final review | Last look before declaring done |

If the user wants to fully automate (skip gates), that's their call to make explicitly — the orchestrator never decides it.

## Failure modes

- **Story file not found** → stop at Stage 0, list `stories/`, ask which file.
- **Slug already has artifacts** → list them, ask skip/replace, default skip (resume).
- **A sub-skill returns `redo`** → re-invoke that skill with the corrective input; don't re-run upstream stages.
- **`FAL_KEY` missing** (Stage 2) or **ElevenLabs MCP unavailable** (Stage 3) → surface the error, suggest setup (README). The publisher can build a partial storybook if only one medium is missing — but ask first.

## What this skill does NOT do

- Does NOT bypass any sub-skill's hard gate.
- Does NOT generate content itself — it only dispatches.
- Does NOT write a story for the user — input is a finished English `.md` (this pipeline illustrates + narrates + exports; it doesn't author).
- Does NOT support multi-story batch runs in one call.

## Reference files

- [scene-splitter/SKILL.md](../scene-splitter/SKILL.md)
- [story-illustrator/SKILL.md](../story-illustrator/SKILL.md)
- [story-narrator/SKILL.md](../story-narrator/SKILL.md)
- [story-html-publisher/SKILL.md](../story-html-publisher/SKILL.md)
