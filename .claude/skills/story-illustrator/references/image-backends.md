# Image Models — the Registry, and Adding / Swapping Models

The illustrator's consistency craft (bible → references → cascading scene images) is **backend-independent**. It only needs one capability:

> **Generate an image from `(prompt, reference_image_urls, aspect_ratio)` and return a file (and a URL) for the result.**

Any image generator that accepts **reference images** can be plugged in. Reference-image support is the hard requirement — it's what carries character/location/state consistency from scene to scene. A model with no reference-image input can still run, but consistency degrades to "describe everything in the prompt every time," which drifts.

This repo talks to **Fal** through one small stdlib script, [assets/fal_image.py](../assets/fal_image.py), driven by a model registry, [assets/image-models.json](../assets/image-models.json). You change models by editing JSON — not code.

## The three operations the skill performs

| # | Operation | Inputs | Output |
|---|---|---|---|
| 1 | Generate a **reference** | style descriptor + character/location description + no-text/no-border rules + aspect ratio | image (file + URL) |
| 2 | Generate a **scene** | scene prompt + ordered reference URLs (chars → location → previous scene) + aspect ratio | image (file + URL) |
| 3 | **Retry** a scene | corrective prompt + [previous attempt URL, char refs, location ref] + aspect ratio | image (file + URL) |

All three are the same primitive — one `fal_image.py` call with different prompts and `--ref` lists.

---

## The script

```bash
python .claude/skills/story-illustrator/assets/fal_image.py \
  --model <key from image-models.json> \
  --aspect 4:5 \
  --prompt "<style> <body> <no-text + no-border>" \
  --ref <url> --ref <url> --ref <url> \
  --out stories/<slug>/<slug>_images/part_03.png
```

- **Auth:** reads `FAL_KEY` from the environment or a `.env` at the repo root. `--check` reports whether a key is resolvable (no spend); `--dry-run` prints the exact request body without calling Fal.
- **What it does:** submits to Fal's queue API (`POST https://queue.fal.run/{endpoint}`), polls the returned `status_url` until `COMPLETED`, GETs the `response_url`, then **downloads** `images[0].url` to `--out`.
- **What it prints:** one JSON line — `{"url": "...", "path": "...", "model": "...", "cost_usd": 0.08}`. Store **both**: `path` is the durable local file the publisher embeds; `url` is the fresh Fal CDN URL reused as a cascade reference during the run.
- **References flow as URLs.** Generated references and scene images come back as Fal URLs, so the cascade just passes those URLs as `--ref` — no uploading. (The local `path` copies exist for durability + QA.)

## The registry

`image-models.json` is a map of friendly keys → model config:

```jsonc
{
  "default": "nano-banana-2",
  "references_model": "nano-banana-2",          // cheapest reference-capable model
  "multi_character_model": "nano-banana-pro",   // used by the "smart mix" policy
  "models": {
    "nano-banana-2":   { "endpoint": "fal-ai/nano-banana-2/edit",            "supports_refs": true, "aspect_param": "aspect_ratio", "resolution": "1K", "cost_per_image_usd": 0.08 },
    "nano-banana-pro": { "endpoint": "fal-ai/nano-banana-pro/edit",          "supports_refs": true, "aspect_param": "aspect_ratio", "resolution": "1K", "cost_per_image_usd": 0.15 },
    "seedream-4":      { "endpoint": "fal-ai/bytedance/seedream/v4/edit",    "supports_refs": true, "aspect_param": "image_size", "image_size_long_edge": 2048, "cost_per_image_usd": 0.03 }
  }
}
```

Field meanings:

| Field | Meaning |
|---|---|
| `endpoint` | The Fal model id. **Use a reference-capable variant** (usually the `/edit` endpoint) so it accepts `image_urls`. |
| `supports_refs` | Must be `true` for the cascade. The script refuses to pass `--ref` to a model without it. |
| `max_refs` | Most reference images the model accepts. **nano-banana models cap at 4**; seedream allows ~10. The script errors clearly if you exceed it (instead of Fal's opaque "no_media_generated"). On a SOFT cut that would exceed the cap, drop the standalone location ref — the previous-scene ref carries the location. |
| `aspect_param` | How this model encodes aspect ratio: `aspect_ratio` (pass the string `"4:5"`) or `image_size` (the script computes `{width,height}`). |
| `resolution` | For `aspect_ratio` models: Fal resolution tier (`1K` keeps cost at the base rate). |
| `image_size_long_edge` | For `image_size` models: the long edge in px the script targets. |
| `cost_per_image_usd` | Used for the gate estimates. Keep it honest so the dollar estimates are real. |

## Adding a new Fal model

1. Find the model on [fal.ai/models](https://fal.ai/models). Open its **`/edit`** (image-to-image) API page — you need the variant that takes `image_urls`.
2. Note its endpoint id, how it takes aspect/size (`aspect_ratio` vs `image_size`), and its price.
3. Add an entry to `image-models.json` with `supports_refs: true`.
4. Try it: `python fal_image.py --model <key> --aspect 4:5 --prompt "..." --ref <url> --out /tmp/x.png --dry-run` to eyeball the request, then drop `--dry-run` to generate for real.

That's it — the skill can now use `<key>` at the model gate. The bible, shot list, continuity classes, no-text/no-border rules, and the `{slug}_images.json` schema are all unchanged.

## Using a completely different provider (not Fal)

Keep the contract — *(prompt, reference URLs, aspect) → a saved file + a URL, printed as one JSON line* — and you can point the skill anywhere:

- **Another HTTP API** (OpenAI images, Replicate, a self-hosted model): write a sibling script with the same CLI and JSON output, or extend `fal_image.py` to branch on a `provider` field in the registry.
- **An MCP image server** that exposes a `generate_image`-style tool with reference images: call the tool instead of the script; capture its returned URL, download it locally, and write the same `{path, url, model}` into `images.json`.

### Checklist for any new provider

1. **Connectivity check** — an equivalent of `--check` (is the key/server present?). Run it at Stage 1; stop if unavailable.
2. **Reference-image input** — by URL or upload? Note the **max** number of references it accepts.
3. **Aspect ratio** — supported values; map `4:5 / 1:1 / 3:4 / 16:9` to its nearest size.
4. **Sync vs. async** — direct return, or a job you poll? Wrap polling like `fal_image.py` does.
5. **Output** — URL or bytes? Always save a local file and record its `path` (the publisher embeds the file, so a stale URL never breaks the storybook).
6. **Cost note** — record per-image cost so the gate estimates stay honest.

### What stays identical regardless of provider

- The **bible** and **shot list** (`bible-extraction.md`, `shot-list.md`)
- The **continuity classification** (HARD / SOFT / MICRO / STATE RESET) and the **reference ordering**
- The **no-text + no-border** universal prompt rules
- The **`{slug}_images.json`** schema and the scene-index pairing with audio
- The **retry pattern** (`qa-and-retry.md`) — previous attempt as the primary reference

Only the literal "make one image" call changes. Keep the references and the cascading logic and consistency holds on any capable model.

---

## If a model has NO reference-image support

Consistency will be weaker, but you can still produce a storybook:
- Put the **full, verbatim** character and location descriptions from the bible into **every** scene prompt (the one time you ignore the anti-redundancy rule).
- Use a fixed **seed** (`--seed`) to reduce variation.
- Expect more drift and budget more retries.
- Strongly prefer a reference-capable model for anything beyond a quick demo — it's the difference between "a storybook" and "a slideshow of different children."
