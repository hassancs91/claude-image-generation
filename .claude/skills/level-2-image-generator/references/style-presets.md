# Style Presets

Pick ONE preset per render based on the prompt. Each preset lists renderer
exposure, lighting levels, fog, sky colors, and material constraints. The
per-style exposure and envMapIntensity values are calibrated — do not reuse
dark-style values in light styles or vice versa.

Pass `exposure` into `createRenderer(aspect, { exposure })`.

---

## 1. Dark Studio (product commercials, tech, dramatic)

Trigger words: product render, commercial, glossy, studio, dramatic, tech, neon accents.

```js
exposure: 1.25
scene.fog = new THREE.FogExp2(0x07060f, 0.012);
addStudioEnvironment(renderer, scene);   // required for gloss

// Sky sphere gradient: top 0x1b1440 → bottom 0x07060f
// + additive halo disc behind the hero (primary color, alpha ~0.5 falloff pow 2.6)

// Lights
AmbientLight(0x8890c8, 0.25)
DirectionalLight(0xfff4e6, 1.7) key at (5,9,6), castShadow, shadow.radius 6
DirectionalLight(0x06b6d4, 2.4) cyan rim at (-7,4.5,-6)
DirectionalLight(0x8b5cf6, 1.8) violet rim at (7.5,3,-5)
HemisphereLight(0x5560c0, 0x0a0a14, 0.35)

// Materials: MeshPhysicalMaterial clearcoat 1.0, roughness ~0.16,
// envMapIntensity 1.35. Emissive accent rings (emissiveIntensity 2-3) allowed.
// Floor: dark glossy, transparent opacity 0.72 + mirrored-clone fake reflection
// at opacity 0.16 (see geometry-recipes.md).
```

## 2. Apple Light (clean, minimal, high-key white studio)

Trigger words: apple style, light, white, clean, minimal, elegant.

```js
exposure: 1.08          // NOT higher — high-key scenes wash out fast
// NO fog
addStudioEnvironment(renderer, scene);

// Sky: white 0xffffff → 0xe2e4e9, optional whisper pastel wash
// (blush 0xffd9c9 left, sky-blue 0xcfe3ff right, mix factor <= 0.22)

// Lights (LOW ambient is the point — form needs shading to read on white)
AmbientLight(0xffffff, 0.32)
DirectionalLight(0xffffff, 1.15) key at (4,10,7), shadow.radius 10
DirectionalLight(0xffffff, 0.32) fill at (-7,5,5)
DirectionalLight(0xdfe9ff, 0.7) cool edge at (-3,7,-7)
HemisphereLight(0xffffff, 0xc8cad2, 0.35)

// Materials: HARD RULE — the hero needs at least one metallic or mid-gray
// material family. Pure white/matte-white plastic DISAPPEARS on white.
// aluminum: color 0xaeb2b9, metalness 0.95, roughness 0.34, envMapIntensity 1.1
// light shell: 0xc7cbd1, metalness 0.9, roughness 0.38
// No emissive accents. Contact shadow gray-blue (0.32,0.34,0.4), never black.
```

## 3. Outdoor / Nature (daylight)

Trigger words: tree, meadow, forest, landscape, garden, nature, park, animals outdoors.

```js
exposure: 1.15
scene.fog = new THREE.FogExp2(0xd8e6dc, 0.0075);
// environment map optional; keep envMapIntensity <= 0.3 on all materials

// Sky: 0x6db4e8 → horizon 0xf2e8d5, sun glow pow(dot(n,sunDir),18)*0.55

// Lights
AmbientLight(0xbdd4e8, 0.3)
DirectionalLight(0xfff0d8, 1.55) sun at (28,32,18), 4096 shadow map,
  shadow camera bounds ±25, bias -0.0004
HemisphereLight(0x9ecdf0, 0x50703c, 0.55)
DirectionalLight(0xffe8cc, 0.35) warm rim at (-20,12,-18)

// Materials: MeshStandardMaterial roughness 0.9+, metalness 0.
```

## 4. Sunset / Golden Hour

```js
exposure: 1.3
scene.fog = new THREE.FogExp2(0xffccaa, 0.009);

// Sky: 0xff9966 → 0xffccaa, strong sun glow low on horizon
AmbientLight(0xffd0a8, 0.35)
DirectionalLight(0xffaa55, 1.7) low sun at (35,10,20) — long shadows
HemisphereLight(0xff9966, 0x4a3828, 0.4)
// Materials warm-shifted; rim lighting on silhouettes reads beautifully here.
```

## 5. Night / Moonlit

```js
exposure: 0.85
scene.fog = new THREE.FogExp2(0x0a1628, 0.018);

// Sky: 0x0a1628 → 0x1a2840, add instanced star points (MeshBasicMaterial,
// additive, tiny scales)
AmbientLight(0x334466, 0.3)
DirectionalLight(0xaaccff, 0.9) moon at (-20,30,10), cool shadows
HemisphereLight(0x223355, 0x0a0a14, 0.3)
// Emissive windows/lanterns (0xffbb66, intensity 2+) carry the composition.
```

## 6. Underwater

```js
exposure: 0.9
scene.fog = new THREE.FogExp2(0x006994, 0.028);   // fog IS the water

// Sky sphere: 0x66ccff top (surface light) → 0x003355 bottom
AmbientLight(0x4488aa, 0.5)
DirectionalLight(0xaaddff, 1.2) from above (0,40,10)
// God-ray fakes: tall additive transparent cones from above, opacity ~0.06
// Floating particulate: 150+ instanced motes, additive, slight opacity.
```

---

## Cross-style rules

- SSAA is always on (ss=2 default in pipeline). Never rely on MSAA.
- ACES tone mapping is set by the pipeline; only exposure varies per style.
- All glow = emissive materials + additive blending + fog. No post-processing,
  no EffectComposer, no bloom passes.
- PCFSoft shadows are set by the pipeline. One shadow-casting light per scene.
- For 9:16 (vertical), raise camera FOV by ~6° and frame the hero in the
  vertical center-third; for 1:1 keep the hero centered with ~15% margin.
