---
name: cf-image
description: Generate an image from a text description using Cloudflare Workers AI (the flux-1-schnell model). Use this skill whenever the user wants to create, generate, make, or draw an image / picture / logo / icon / thumbnail / wallpaper / banner from a text idea and mentions Cloudflare, or is working in this repo and asks for a quick generated image. Claude expands the user's request into a strong image prompt, runs the bundled generate.py, and saves a JPG to disk. Trigger on phrases like "generate an image of", "make me a picture of", "create a thumbnail for", "cloudflare image", or a plain description paired with a request for an image. Requires CF_ACCOUNT_ID and CF_API_TOKEN in the project's .env.
---

# cf-image

Turn a natural-language request into a generated image using **Cloudflare Workers AI** (`@cf/black-forest-labs/flux-1-schnell`). This skill is the "connect Claude to image generation" loop: the user describes what they want, Claude does the prompt engineering, the bundled script calls the Cloudflare API, and the image is saved locally.

## When this skill applies

The user wants an image generated from a description — e.g. "generate a logo idea for a coffee shop", "make a thumbnail for my AI video", "picture of a cyberpunk cat". Claude is responsible for turning a vague ask into a good prompt before generating.

It does **not** apply to: editing an existing image, vector/SVG art, or video.

## How to run it

From the repo root:

```bash
python .claude/skills/level-3-image-generator/generate.py "<optimized prompt>" -o <filename>.jpg
```

- `"<optimized prompt>"` — the prompt **you** write (see below), not the user's raw words.
- `-o` / `--output` — where to save (default `out.jpg`). Pick a short descriptive name, e.g. `coffee-logo.jpg`.
- `--steps` — diffusion steps (default `4`). flux-schnell is tuned for few steps; 4–8 is plenty. Higher is slower, not always better.

The script prints `Saved <file> ...` on success, or a Cloudflare API error message on failure.

## The one job Claude must do: write a strong prompt

The raw script would need a hand-written prompt. The value of this skill is that **Claude expands the user's intent into a vivid, specific prompt** before calling the script. A good Flux prompt names:

- **Subject** — what's in the frame, concretely.
- **Style/medium** — photo, 3D render, flat vector, watercolor, isometric, etc.
- **Composition & framing** — close-up, wide shot, centered, rule-of-thirds.
- **Lighting & mood** — golden hour, neon, soft studio light, dramatic shadows.
- **Color/detail cues** — palette, background, level of detail.

Example transformation:
- User: *"a logo for a coffee shop"*
- Prompt you pass: *"minimalist logo of a steaming coffee cup, flat vector illustration, warm brown and cream palette, centered on a clean off-white background, simple bold shapes, modern branding"*

Keep prompts to one or two sentences. Don't include text/words to render — Flux is unreliable at rendering legible text.

## After generating

1. Confirm the file was saved (the script prints the path).
2. Tell the user the filename and the exact prompt you used, so they can tweak and re-run.
3. If they want variations, re-run with a modified prompt and a new `-o` filename.

## Requirements

- `CF_ACCOUNT_ID` and `CF_API_TOKEN` set in the project's `.env` (see `.env.example`). The script loads them automatically.
- Python deps: `requests`, `python-dotenv`.
