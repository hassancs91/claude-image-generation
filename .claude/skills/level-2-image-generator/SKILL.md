---
name: 3d-image-renderer
description: Generate PNG images by building a real Three.js 3D scene and capturing one frame headlessly — no image model involved. Takes a text prompt and an aspect ratio (1:1, 16:9, or 9:16) and produces a rendered PNG. Use this skill whenever the user asks to generate, create, or render an image, picture, scene, wallpaper, thumbnail background, or product shot with this system — especially with phrases like "generate an image of", "render a scene", "create a PNG", "no image model", "3D render of", or a prompt paired with an aspect ratio. Also use it when the user wants an image in a named visual style (dark studio, Apple light, nature, sunset, night, underwater). Not for editing existing images, 2D vector art, or animated video (VidTSX handles video).
---

# 3D Image Renderer

Renders a text prompt into a PNG by writing a Three.js scene and capturing
one frame with headless-gl under Xvfb. Think of every image as frame 0 of a
TSX animation composition: deterministic, seeded, time = 2.0s.

## Inputs

- **prompt** — what to render
- **aspect ratio** — one of `1:1` (1080×1080), `16:9` (1920×1080), `9:16`
  (1080×1920). Default `16:9` if unspecified. No custom sizes.

## Workflow (follow in order)

### 1. Setup

```bash
bash <skill_dir>/scripts/setup.sh
```

Idempotent; instant when cached. Installs npm deps into
`/home/claude/scene-render/` and drops the bundled prebuilt `gl` binary in
place (compiles from source only if the binary fails its smoke test). It also
copies `pipeline.mjs` and `validate.mjs` into the workdir. If it prints
`SETUP FAILED`, report the error to the user — do not hand-roll a fallback.

### 2. Plan the scene

- Pick ONE style preset → read `references/style-presets.md` now.
- List the **hero elements**: every concrete noun in the prompt
  ("headphones", "tree", "flowers") is a hero element.
- Read `references/geometry-recipes.md` for any element it covers before
  inventing geometry.

### 3. Write the scene

Create `/home/claude/scene-render/scene.mjs`. Import ONLY from the local
pipeline — never re-implement renderer setup, pixel readback, or PNG writing:

```js
import {
  THREE, createRenderer, captureFrame, addStudioEnvironment,
  seededRandom, visibleHeightAt,
} from './pipeline.mjs';

const time = 2.0; // the captured "frame"
const { renderer, glContext, W, H, OUT_W, OUT_H } =
  createRenderer('16:9', { exposure: 1.15 /* from style preset */ });

const scene = new THREE.Scene();
// ... build: sky, lights, ground, hero elements (per preset + recipes) ...

await captureFrame({
  renderer, glContext, scene, camera, W, H, OUT_W, OUT_H,
  outPath: '/home/claude/scene-render/out.png',
});
console.log('DONE');
```

Scene-authoring rules:
- All randomness via `seededRandom(seed)` — never `Math.random()`.
- `InstancedMesh` for anything repeated 50+ times; per-instance color via
  `setColorAt` + `instanceColor.needsUpdate = true`.
- Bake rotations into geometry (`geometry.rotateZ(...)`) — do not stack Euler
  rotations on meshes for construction.
- Validate every horizon/background element with `visibleHeightAt` (the FOV
  rule in geometry-recipes.md) BEFORE rendering.
- No post-processing. Glow = emissive + additive blending + fog.
- WebGL1 only: no `transmission`, no WebGL2-only features, three stays at
  0.152.2 (pinned by setup — do not upgrade).

### 4. Render

```bash
cd /home/claude/scene-render && xvfb-run -a node scene.mjs
```

### 5. Validate (mandatory — never skip)

Write a hero spec covering each prompt-named element with its dominant
material color, then:

```bash
node validate.mjs out.png heroes.json
```

```json
[
  { "name": "flowers", "hex": "f5a8c8", "tolerance": 45, "minPct": 0.3 },
  { "name": "tree canopy", "hex": "5a9440", "tolerance": 60, "minPct": 2.0 }
]
```

Also open the PNG with the view tool if image viewing works in this session.
If it returns placeholders, rely on the validator output (histogram, ASCII
map, presence checks) — it was designed for exactly that.

Fix and re-render when:
- any hero element FAILs presence (typical fixes: more instances, bigger
  scale, camera reframe, contrasting material)
- WASHED OUT / TOO DARK / LOW CONTRAST warnings (typical fixes: exposure and
  ambient per the style preset table; in light styles swap pure-white
  materials for metallic/mid-gray)
- the ASCII map shows a composition failure (subject cropped, background
  walling off the sky)

Maximum 2 fix iterations, then deliver best result and tell the user what
still needs work.

### 6. Deliver

```bash
cp /home/claude/scene-render/out.png "/mnt/user-data/outputs/<descriptive_name>.png"
```

Present the PNG with `present_files`. Keep the summary short: style preset
used, hero elements, and any validation fixes applied. Only include
`scene.mjs` in the delivery if the user asks for the code.

## Hard rules (violating any of these produced real failures)

1. three@0.152.2 pinned — r163+ drops WebGL1 and headless-gl is WebGL1-only.
2. Pixel readback needs vertical flip + alpha forced to 255 (pipeline does it).
3. No MSAA headless — SSAA 2× via the pipeline is the anti-aliasing.
4. Light styles: exposure ≤ 1.08, ambient ≤ 0.35, and the hero MUST include a
   metallic or mid-gray material. Pure white on white is invisible.
5. Background elements sized by intuition WILL wall off the sky — run the FOV
   check.
6. Prompt-named elements must pass the presence validator before delivery.
7. Everything deterministic: `seededRandom`, fixed `time = 2.0`.
