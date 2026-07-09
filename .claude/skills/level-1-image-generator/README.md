# prompt-to-design

A Claude **Agent Skill** that turns a text prompt + an aspect ratio into a polished
PNG graphic — built entirely from code (gradients, mesh fields, glow, grain, shapes,
and real typography), not a diffusion/photo model.

Think of it as an image generator with a strong house style: **designed graphics**.

## What it makes well

Posters & album art · quote / story / reel / carousel covers · phone & desktop
wallpapers · gradient & mesh backgrounds · neon / synthwave / vaporwave ·
Bauhaus / Swiss geometric art · minimalist marks & patterns · soft "product"
visuals · anything **typographic**. Text is crisp, alignment is perfect, and there
are no AI artifacts.

## What it can't do

It is not a photo model. It **cannot** produce photorealism, a specific real
person's face, brand logos, or copyrighted characters. Ask for one of those and it
will give you a strong stylized/typographic take instead.

## How to use

Once the skill is installed, just ask in plain language and give a size:

- "Generate a **synthwave poster**, chrome title *NEON HORIZON*, **1:2**."
- "Make a **quote card**: *'Build quietly. Let the work make the noise.'* — premium
  story cover, **9:16**."
- "A **Bauhaus geometric** composition, bold primaries, **1:1**."
- "**Soft Apple-style** carousel slide, pastel orb, headline *'Designed to feel
  effortless.'* — **1:1**."
- "**Minimalist sunset over mountains**, warm dusk, poster, **16:9**."
- "A **dreamy mesh gradient** wallpaper, teal & violet, **9:16**."

You describe everything in the prompt (subject, mood, colors, any words to render),
the same way you'd prompt an image model. If you don't give a ratio, it defaults to
**1:1**.

### Aspect ratios

`1:1` (default) · `4:5` · `9:16` · `16:9` · `2:3` · `3:2` · `1:2` · `3:4` · `4:3` ·
`5:4` · `2:1`, or a custom `WxH` (e.g. `1600x1000`).

## Installing

This folder is a self-contained Agent Skill. Install it wherever your Claude reads
skills (e.g. upload/add it in the Skills panel of the Claude app, or place the
`prompt-to-design/` folder in your skills directory). It needs Python with
**Pillow** and **numpy** available in the execution environment; the fonts it uses
are bundled in `fonts/`.

## What's inside

```
prompt-to-design/
├── SKILL.md              # the playbook Claude follows
├── lib/
│   ├── render.py         # the code-based design engine
│   └── fonts.py          # role-based font registry
├── fonts/                # bundled OFL fonts + their license files
└── reference/            # four runnable, gold-standard example builds
```

## Fonts & license

All bundled fonts are licensed under the **SIL Open Font License 1.1**; each
family's `*-OFL.txt` license file ships alongside it in `fonts/`. The skill code
itself is provided for you to use and adapt.
