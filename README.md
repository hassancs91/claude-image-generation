# Claude × Image Generation

Connect Claude to image generation with [Claude Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) — from zero-cost, code-only rendering up to a real diffusion model, then composed into a full app: an **AI Storybook pipeline** that turns a plain-English story into an illustrated, narrated, self-contained HTML book.

<p align="center">
  <img src="level-1-2-3-comparison/coffee-logo-prompt-to-design.png" height="250" alt="Level 1 — code-based design engine">
  <img src="level-1-2-3-comparison/coffee-logo-3d-render.png" height="250" alt="Level 2 — Three.js 3D render">
  <img src="level-1-2-3-comparison/coffee-logo.jpg" height="250" alt="Level 3 — diffusion model">
</p>
<p align="center"><em>One prompt — “a minimalist logo for a coffee shop” — rendered three ways:<br><b>Level 1</b> code-based design engine · <b>Level 2</b> Three.js 3D scene · <b>Level 3</b> diffusion model.</em></p>

The through-line of every skill here is the same: **Claude does the prompt engineering and orchestration**, not just a raw API call. You describe what you want in plain language; Claude turns it into a strong prompt / scene / plan, runs the right tool, verifies the result, and hands you the file.

```
your idea  →  Claude plans & prompts  →  the right generator  →  verified output
```

## Two things this repo teaches

1. **Image generation, three ways (Levels 1–3)** — the *same* "generate an image" request, solved with three very different engines, from free-and-local to a hosted diffusion model.
2. **Composing skills into an app (the Storybook pipeline)** — five skills chained end-to-end into one product.

---

## Part 1 — Image generation in three levels

The three level skills all answer "make me an image," but trade off cost, realism, and control very differently.

| Level | Skill folder | Engine | Needs an API? | Great for |
|-------|--------------|--------|---------------|-----------|
| **1** | [`level-1-image-generator/`](.claude/skills/level-1-image-generator/) | **Code-based design engine** — Pillow + numpy draw gradients, mesh fields, glow, grain, shapes, and real typography. No image model. | ❌ Free / local | Posters, quote & story/reel covers, carousel slides, wallpapers, Bauhaus/Swiss geometric art, neon/synthwave, soft product visuals — anything **typographic or designed**. Crisp text, no AI artifacts. |
| **2** | [`level-2-image-generator/`](.claude/skills/level-2-image-generator/) | **Real Three.js 3D scene**, rendered to one frame headlessly (headless-gl under Xvfb). No image model. | ❌ Free / local (Node) | 3D product shots, rendered scenes, wallpapers, thumbnail backgrounds in named styles (dark studio, Apple light, nature, sunset, underwater). |
| **3** | [`level-3-image-generator/`](.claude/skills/level-3-image-generator/) | **Diffusion model** — Cloudflare Workers AI (`flux-1-schnell`). A hosted image model. | ✅ Cloudflare keys | Photographic / illustrative looks, freeform subjects, logos & icons, quick thumbnails — anything a diffusion model does well. |

> **Why levels?** Levels 1 and 2 never touch an image model — they *construct* the picture from code, so they're free, deterministic, and perfect at text and geometry. Level 3 is the "classic" approach: hand a prompt to a diffusion model. Different jobs want different levels.

### Level 1 — the code-based design engine

<p align="center">
  <img src="level1-examples/synthwave_poster.png" height="240" alt="Synthwave NEON HORIZON poster">
  <img src="level1-examples/quote_card.png" height="240" alt="Quote card — Build quietly. Let the work make the noise.">
  <img src="level1-examples/geometric_art.png" height="240" alt="Bauhaus geometric composition">
  <img src="level1-examples/carousel_slide.png" height="240" alt="Soft Apple-style carousel slide">
</p>

*Everything above is drawn with math and type — no image model. Crisp text, perfect alignment, no AI artifacts.* → [`level1-examples/`](level1-examples/)

### Level 2 — the Three.js 3D renderer

<p align="center">
  <img src="level2-examples/rocket_launch_station_pixar_16x9.png" height="170" alt="Low-poly rocket launch station at dusk">
  <img src="level2-examples/headphones_apple_light_1x1.png" height="170" alt="Studio-lit 3D headphones, Apple-light style">
  <img src="level2-examples/tree_flowers_16x9.png" height="170" alt="3D tree and flowers scene">
</p>

*A real 3D scene, built in code and captured as one frame — still no image model.* → [`level2-examples/`](level2-examples/)

### Level 3 — the diffusion model (Cloudflare Flux)

<p align="center">
  <img src="level3-examples/bookstore-cafe-rainy-evening.jpg" height="210" alt="Photoreal independent bookstore on a rainy evening">
  <img src="level3-examples/water-bottle-marble.jpg" height="210" alt="Product shot — water bottle on marble">
  <img src="level3-examples/ai-agents-thumbnail-bg.jpg" height="210" alt="Thumbnail background for an AI agents video">
</p>

*A hosted diffusion model doing what it does best — photographic and freeform looks.* → [`level3-examples/`](level3-examples/)

### Same prompt, three engines

[`level-1-2-3-comparison/`](level-1-2-3-comparison/) renders the coffee-shop-logo prompt through all three levels (the trio at the top of this page) — the clearest way to feel the trade-offs.

---

## Part 2 — The AI Storybook pipeline

Building on the image skills, this is a small **application**: give it an English story, get back a single self-contained `.html` storybook — a swipe/tap player with one illustration and one narration clip per scene, all embedded so the file works offline and shares as-is.

<p align="center">
  <img src="stories/the-three-gardeners/the-three-gardeners_images/part_02.png" height="250" alt="Storybook scene — grandmother and children in a flower garden">
  <img src="stories/the-three-gardeners/the-three-gardeners_images/part_05.png" height="250" alt="Storybook scene">
  <img src="stories/the-three-gardeners/the-three-gardeners_images/part_08.png" height="250" alt="Storybook scene">
</p>
<p align="center"><em>Consistent, character-stable illustrations across every scene of <b>“The Three Gardeners.”</b></em></p>

```
stories/{slug}.md
      │
      ▼
1. scene-splitter        → {slug}_scenes.json            split the story into ~8–12 illustratable scenes
2. story-illustrator     → {slug}_images.json (+ images) one consistent image per scene   (Fal image models)
3. story-narrator        → {slug}_audio/*.mp3            one expressive narration clip per scene  (ElevenLabs TTS)
4. story-html-publisher  → {slug}.html                  package everything into one shareable HTML file
```

[`storybook-pipeline/`](.claude/skills/storybook-pipeline/) is the **orchestrator** — one entry point ("make a storybook from this") that dispatches the four component skills in order, locks a shared filename convention so every image and audio clip pairs by scene index, and preserves each step's approval gate (scenes, character bible, narration script all get reviewed before money is spent).

| Skill | Role | Backend |
|-------|------|---------|
| [`scene-splitter/`](.claude/skills/scene-splitter/) | Split a story into numbered scenes (1 image + 1 narration each) | Claude only |
| [`story-illustrator/`](.claude/skills/story-illustrator/) | One consistent image per scene, using cascading reference images for character/location continuity | **Fal** (nano-banana-2/pro, seedream-4) |
| [`story-narrator/`](.claude/skills/story-narrator/) | One expressive MP3 per scene | **ElevenLabs MCP** (`text_to_speech`) |
| [`story-html-publisher/`](.claude/skills/story-html-publisher/) | Consolidate scenes + images + audio into one self-contained HTML player | Claude only |

### Finished examples

Three completed storybooks live in [`stories/`](stories/) — each folder has the deliverable `.html`:

- [`stories/the-three-gardeners/the-three-gardeners.html`](stories/the-three-gardeners/the-three-gardeners.html)
- [`stories/pepper-runs-off/pepper-runs-off.html`](stories/pepper-runs-off/pepper-runs-off.html)
- [`stories/the-little-cloud/the-little-cloud.html`](stories/the-little-cloud/the-little-cloud.html)

Open any of them in a browser to read the finished, narrated storybook.

---

## Project structure

```
claude-image-generation/
├── .claude/skills/
│   ├── level-1-image-generator/    # Level 1 — code-based design engine (Pillow + numpy + fonts)
│   ├── level-2-image-generator/    # Level 2 — Three.js 3D scene, rendered headlessly
│   ├── level-3-image-generator/    # Level 3 — Cloudflare Workers AI (flux-1-schnell) diffusion
│   ├── scene-splitter/             # Storybook step 1 — story → scenes
│   ├── story-illustrator/          # Storybook step 2 — scenes → images (Fal)
│   ├── story-narrator/             # Storybook step 3 — scenes → narration (ElevenLabs)
│   ├── story-html-publisher/       # Storybook step 4 — everything → one .html
│   └── storybook-pipeline/         # Orchestrator for the four storybook skills
├── level1-examples/                # sample outputs, Level 1
├── level2-examples/                # sample outputs, Level 2
├── level3-examples/                # sample outputs, Level 3
├── level-1-2-3-comparison/         # one prompt rendered by all three levels
├── stories/                        # story .md inputs + finished storybook folders
├── .env.example                    # API key template  → copy to .env
└── .mcp.json.example               # MCP server config  → copy to .mcp.json
```

---

## Setup

Open this folder in [Claude Code](https://docs.claude.com/en/docs/claude-code) and the skills are picked up automatically. What each part needs:

### 1. Python (Levels 1 & 3, illustrator helper)

```bash
pip install pillow numpy requests python-dotenv
```

### 2. API keys — copy the template and fill in what you need

```bash
cp .env.example .env
```

| Key | Needed for | Where to get it |
|-----|-----------|-----------------|
| `CF_ACCOUNT_ID`, `CF_API_TOKEN` | **Level 3** (Cloudflare diffusion) | Cloudflare dashboard → *Workers & Pages → Overview* (Account ID) and *My Profile → API Tokens* with **Workers AI** run permission (Token). Free tier works. |
| `FAL_KEY` | **story-illustrator** (storybook images) | [fal.ai](https://fal.ai) dashboard |
| `ELEVENLABS_API_KEY` | **story-narrator** (storybook audio) | [elevenlabs.io](https://elevenlabs.io) — also set it in `.mcp.json` (below) |

*Levels 1 & 2 need no keys.* `.env` is gitignored, so your keys never get committed.

### 3. MCP server for narration (storybook only)

The narrator talks to ElevenLabs over MCP. Copy the template and add your key:

```bash
cp .mcp.json.example .mcp.json
```

Then set `ELEVENLABS_API_KEY` and an output path inside `.mcp.json`. (`.mcp.json` is gitignored — the sanitized `.mcp.json.example` is what's committed.)

### 4. Node (Level 2 only)

Level 2 runs `bash <skill>/scripts/setup.sh` on first use to install its npm deps and drop in the prebuilt WebGL binary — no manual step.

---

## Using it

Just ask Claude in plain language. It picks the matching skill, does the prompt/plan work, runs the generator, verifies, and gives you the file.

**Level 1 — designed graphics**
- *"Generate a synthwave poster, chrome title NEON HORIZON, 1:2."*
- *"Make a quote card: 'Build quietly. Let the work make the noise.' — 9:16."*
- *"A Bauhaus geometric composition, bold primaries, 1:1."*

**Level 2 — 3D renders**
- *"Render a pair of headphones, Apple-light studio style, 1:1."*
- *"3D scene of a rocket launch station, 16:9."*

**Level 3 — diffusion model**
- *"Generate a thumbnail background for a video about AI agents."*
- *"A cozy bookstore café on a rainy evening."*

**Storybook pipeline**
- Drop a story in `stories/my-story.md`, then: *"Run the storybook pipeline on stories/my-story.md."*
- Or a single step: *"Illustrate this story"* / *"Narrate this story."*

You can also run the Level 3 script directly:

```bash
python .claude/skills/level-3-image-generator/generate.py "a cyberpunk cat coding at night" -o cat.jpg
```

---

## How a skill works

A Claude Skill is just a folder with a `SKILL.md`. The YAML frontmatter's `description` tells Claude **when** to use the skill; the markdown body tells it **how**. That's the whole trick here — the body encodes the prompt-engineering, the render/verify loop, and the guardrails, so a vague human request becomes a well-executed generation instead of a passthrough API call.

## A note on secrets

Keep real keys in `.env` and `.mcp.json` only (both gitignored) — never in code or committed config. If a token ever lands in a commit, rotate it at the provider — the value stays recoverable from git history otherwise.
