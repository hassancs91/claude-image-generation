---
name: prompt-to-design
description: >-
  Generate a polished PNG graphic from a text prompt and an aspect ratio. This is
  a CODE-BASED design generator (not a diffusion/photo model): it builds images
  from gradients, mesh fields, glow, grain, geometric shapes, and real typography.
  Use it whenever the user wants to create / generate / make an "image", poster,
  cover, wallpaper, banner, thumbnail, album art, story or reel cover, quote card,
  or any graphic from a description — optionally with words to render and a size
  or ratio (e.g. 1:1, 4:5, 9:16, 16:9, 2:3, 1:2, or WxH). It excels at designed,
  typographic, abstract, gradient, and geometric/Bauhaus/Swiss graphics and soft
  product-style visuals. It CANNOT produce photorealistic photos, real named
  people, brand logos, or copyrighted characters — for those, translate intent
  into a strong designed/stylized take instead.
---

# prompt-to-design

Turn a free-form prompt + an aspect ratio into a finished PNG, built entirely from
code. The house style is the level of the four pieces in `reference/`: posters,
typographic covers, mesh/gradient atmospheres, geometric compositions, soft
product abstractions. Frictionless like an image generator, but bounded to
**designed graphics**.

## What it is (and is not)

Everything is drawn with math and type — no image model. That means:

- **Great at:** posters & album art, quote / story / reel / carousel covers,
  wallpapers, gradient & mesh backgrounds, neon / synthwave, Bauhaus / Swiss
  geometric art, minimalist logos-as-shapes, patterns, soft "product" orbs,
  anything typographic. Crisp text, perfect alignment, editable, no AI artifacts.
- **Cannot do:** photorealism, a specific real person's face, detailed
  representational illustration (a recognizable animal, a fantasy castle), brand
  logos, or copyrighted characters.

**Accept any prompt and always output a designed PNG.** Silently route the prompt
to the rendering approach that fits (see *Style routing*). Only if a prompt truly
demands a photo (e.g. "photorealistic portrait of my friend") say so in one
sentence and deliver the strongest stylized/typographic interpretation anyway —
never refuse, never return a blob that ignores the prompt.

## Inputs

1. **Prompt** — free text. Extract: subject/scene, mood, any color cues, and
   **any literal words to render** (quotes, titles, handles), plus implied style.
2. **Aspect ratio** — a preset or `WxH`. If unspecified, default **1:1**.

## The pipeline (follow in order)

1. **Read the prompt.** Identify subject, mood, palette hints, literal text, ratio.
2. **Route to a style** (one of: *typographic*, *geometric*, *gradient-atmospheric*,
   *soft-minimal*, *poster-scene*) — see below. When ambiguous, pick the one that
   best serves the words + mood.
3. **Choose a palette** (3–6 colors, deliberate). See *Palette*.
4. **Plan the composition** in your head first: the ONE focal element, the
   hierarchy, where the negative space lives. Balance mass with space.
5. **Assign fonts by role** (display / grotesque / geometric / serif / serif_book /
   mono / pixel / techno). See *Typography*.
6. **Write a Python script** that imports the engine and composes the piece
   (pattern below). Prefer the library primitives; drop to numpy only for custom
   effects.
7. **Render to a PNG** in the outputs directory.
8. **VERIFY** (mandatory gate — see *Verify*). Fix issues, re-render.
9. **Present** the PNG. (Do not show the user the internal design reasoning or any
   `.md` notes — PNG only.)

Optionally, thinking through a one-paragraph "design philosophy" for the piece
before coding measurably improves results — do it as internal reasoning, never as
a user-facing file.

## Environment & how to run

Requires Python with **Pillow** and **numpy** (install with
`pip install pillow numpy --break-system-packages` if missing). Fonts are bundled
in `fonts/` — no system fonts needed.

Write a script that puts this skill's `lib/` on the path, composes, and saves:

```python
import sys
sys.path.insert(0, "SKILL_DIR/lib")     # the lib/ folder next to this SKILL.md
from render import Design, NEON, NEON_CYAN, CREAM, INK, CHARCOAL, lerp_stops

d = Design("9:16")                       # preset, "WxH", or (w, h)
# ... compose with d.<method>(...) ...
d.save("/mnt/user-data/outputs/design.png", grain=6, saturation=1.1)
```

Replace `SKILL_DIR` with the absolute path to this skill. Then run with
`python3 your_script.py` and present the saved PNG.

## Engine quick reference (`render.Design`)

Coordinates are fractions: `x` in [0,1] across width, `y` in [0,1] down height.
Sizes / radii / widths / font sizes are in **final pixels**; the engine
supersamples internally and downsamples for crisp edges.

**Construct:** `Design(size="1:1", supersample=None, background=(255,255,255))`

**Backgrounds** (set the whole canvas):
- `fill(color)`
- `linear_gradient(stops, angle=90)` — `stops=[(pos,(r,g,b)),...]`; 90=top→bottom, 0=left→right
- `radial_gradient(stops, center=(0.5,0.5), radius=0.9)`
- `mesh_gradient(points)` — `points=[(fx,fy,(r,g,b),sigma_frac),...]` smooth blended color fields
- `overlay_glow(center,color,radius,strength=0.4,mode="screen"|"add"|"blend")` — soft glow onto current canvas
- `vignette(strength=0.4, center=(0.5,0.5), radius=0.75, power=1.6)`

**Shapes** (optional `glow={"color":(r,g,b)}` for neon):
- `disk(cx,cy,r,color,glow=)` · `ellipse(cx,cy,rx,ry,color)` · `ring(cx,cy,r,width,color)`
- `pie(cx,cy,r,a0,a1,color)` — filled arc/sector; angles: 0=east, CW; top half=180→360, bottom=0→180
- `arc(cx,cy,r,a0,a1,width,color)` — open stroke arc
- `rect(x0,y0,x1,y1,color,radius=0)` — `radius>0` for rounded/pills
- `line(x0,y0,x1,y1,width,color)` · `polygon([(x,y),...],color)`
- `intersection(shapeA, shapeB, color)` — knockout the overlap; shapes are
  `("disk",cx,cy,r)`, `("pie",cx,cy,r,a0,a1)`, `("rect",x0,y0,x1,y1)`

**Soft orb:** `gradient_sphere(cx,cy,r, colors, light=(-0.34,-0.34), shadow=True,
specular=0.16, rim=0.05, glow=None)` — `colors` = 2–3 stops blended diagonally.

**Type:**
- `write(x,y,text, role=, weight="regular"|"bold", italic=False, size=, color=,
  gradient=None, align="left"|"center"|"right", tracking=0, glow=None, shadow=None,
  stroke=0, stroke_color=None, return_width=False)` — one line; `y` is the baseline.
  Pass `gradient=[(pos,(r,g,b)),...]` for **chrome/metal** fills; `glow={"color":...}`
  for neon; `shadow=True` or a dict for legibility on busy backgrounds.
- `text_block(x,y,text, ..., max_frac=0.84, line_height=1.16)` — auto-wraps & stacks.
- `fit_size(text, target_frac, role=, weight=)` → largest size that fits that width.
- `wrap(text, max_frac, ...)` → list of lines. `measure(text, ...)` → (w,h) in final px.

**Custom numpy:** `coords()`→(xx,yy) · `get_rgb()` · `set_rgb(arr)` · `composite_rgba(arr)`.

**Finish:** `save(path, grain=0, chroma=0, scanlines=0, saturation=1.0, contrast=1.0,
brightness=1.0)` — post effects are applied after downsample (correct place for grain).
Typical: light designs `grain=2`; rich/dark designs `grain=5–6, chroma=2`; add
`scanlines=0.03` only for CRT/retro looks.

## Style routing

- **typographic** — prompt centers on words/a quote/a title, or asks for a "quote
  card", "cover", "poster with text". Huge fitted type is the hero over a gradient
  or mesh. Emphasize one word (color or serif italic). *(ref: quote_card.py)*
- **geometric** — "Bauhaus", "Swiss", "geometric", "shapes", "minimal poster",
  abstract mark. Flat color fields, circles/arcs/lines on a grid, knockouts,
  generous whitespace. *(ref: geometric_bauhaus.py)*
- **gradient-atmospheric** — "gradient", "mesh", "aurora", "synthwave", "vaporwave",
  "neon", "dreamy", "abstract background", wallpaper. Mesh/linear fields + glow +
  grain; add shapes/type as needed. *(ref: synthwave_poster.py)*
- **soft-minimal** — "soft", "Apple", "clean", "pastel", "premium", "carousel
  slide", "product". Light airy ground, a soft `gradient_sphere` or rounded card,
  refined type, lots of space. *(ref: soft_carousel.py)*
- **poster-scene** — a simple scene ("sunset over mountains", "ocean horizon",
  "desert dunes"). Render as flat/geometric layers: gradient sky, a `pie`/`disk`
  sun, `polygon` mountains, layered bands — a stylized *designed* landscape, not a
  photo. Combine gradient + shapes.

Most prompts blend two (e.g. a synthwave poster is gradient-atmospheric +
typographic). Compose accordingly.

## Palette

Pick 3–6 colors that carry a clear mood; restraint reads as premium.
- Warm/energetic: vermilion, coral, gold, magenta.
- Cool/calm: indigo, cobalt, teal, periwinkle.
- Neon: hot magenta + cyan on near-black.
- Soft/premium: cream/paper ground, muted pastels, one gentle accent.
- Bauhaus: cream + primary red/blue/yellow + ink (+ optional teal).
Use a light ground for airy/editorial; a dark or saturated ground for punchy/neon.
Ensure text contrast (see Verify). Grain/dither prevents banding in smooth fields.

## Typography

- Match the face to the mood: `display`/`display_chunky` for huge poster words;
  `grotesque`/`geometric` for clean modern/Apple; `serif`/`serif_display`/`serif_chic`
  for editorial/elegant; `serif_book` italic for a graceful accent word;
  `mono` for kickers/handles/labels; `pixel` for retro-arcade; `techno` for sci-fi.
- Make hero type genuinely large — use `fit_size` so the longest line fills the
  column. Break a phrase into short lines for tall formats.
- Mix sparingly: one hero face + one label face; emphasize at most one word.
- On busy/gradient grounds, give type a soft `shadow` or `glow` for legibility.
- Add a small letter-spaced kicker and/or a small footer to sell "designed piece"
  — but keep them quiet.

## Verify (mandatory before presenting)

After rendering, always check the result. Prefer viewing the PNG. **If the image
viewer is unavailable or returns nothing, fall back to measuring pixels** (this is
reliable and catches real bugs):

- **Legibility:** sample the background luminance behind the text vs the text
  color — ensure strong contrast. Light text needs a dark-enough ground (and/or a
  shadow/glow); dark text needs a light ground.
- **Presence & placement:** scan for the key colors (e.g. count pixels near the
  accent/headline color) and print their bounding box to confirm elements landed
  where intended and nothing was accidentally covered or knocked out.
- **Composition:** downsample to a ~44-wide grid and print a coarse "map"
  (nearest-palette letters, or a luminance ramp) to see balance, coverage, and
  whitespace at a glance.
- **Banding:** ensure grain/chroma is on for smooth gradients.

Example checks:
```python
from PIL import Image; import numpy as np
a = np.array(Image.open(path).convert("RGB")).astype(int)
lum = 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
band = lum[int(.3*a.shape[0]):int(.7*a.shape[0])]          # text band
print("bg lum behind text:", round(band[band<200].mean()))  # compare to text lum
mask = (((a-np.array(ACCENT))**2).sum(2) < 1500)            # find an element
ys,xs = np.where(mask); print("accent bbox:", xs.min(),xs.max(),ys.min(),ys.max())
```
Common bugs to look for (all seen in practice): a knockout `intersection` that
swallows a whole shape because one shape sits fully inside the other; text/caption
placed on same-color area so it's invisible; a hero element too small; a gradient
that's so dark/muddy the colors don't read (lift it / boost saturation). Fix and
re-render until it's clean.

## Aspect ratios

| Preset | Pixels | Typical use |
|---|---|---|
| 1:1 | 1500×1500 | square post (**default**) |
| 4:5 | 1080×1350 | IG portrait |
| 9:16 | 1080×1920 | story / reel / phone wallpaper |
| 16:9 | 1920×1080 | slide / desktop / YouTube |
| 2:3 | 1200×1800 | poster portrait |
| 3:2 | 1800×1200 | poster landscape |
| 1:2 | 1080×2160 | tall poster |
| 3:4, 4:3, 5:4, 2:1 | — | also available |

Or pass `WxH` (e.g. `"1600x1000"`), clamped to a 2560 long edge for speed.

## Guardrails

No photorealistic depictions of real, named people; no reproductions of brand
logos or trademarks; no copyrighted characters or existing artworks; nothing
harmful. These are designed original graphics. When a prompt asks for one of
these, deliver an abstract/typographic/stylized interpretation instead and say so
briefly.

## Reference examples

Study `reference/` — each is a runnable, gold-standard build for a prompt type:

- `synthwave_poster.py` — gradient sky, striped sun, neon grid, chrome title (1:2)
- `geometric_bauhaus.py` — flat fields, arcs, knockouts, dot grid (1:1)
- `quote_card.py` — mesh gradient + huge type + italic/gold accents (9:16)
- `soft_carousel.py` — light ground, soft orb, refined type, page dots (1:1)

When a new prompt resembles one, start from its structure and adapt palette,
composition, copy, and ratio.
