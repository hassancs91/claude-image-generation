# Geometry Recipes

Proven scene-building patterns. Copy these rather than inventing new
approaches — each encodes a fix for a real failure.

## Contents
1. Product studio stage (floor, fake reflection, contact shadow, halo)
2. Recursive tree
3. Instanced grass / flowers / foliage
4. Horizon elements & the FOV rule
5. Rotation gotchas
6. Common hero objects

---

## 1. Product studio stage

```js
// Floor: semi-transparent so the mirrored reflection reads through it
const floor = new THREE.Mesh(
  new THREE.CircleGeometry(40, 64),
  new THREE.MeshPhysicalMaterial({
    color: 0x0b0d1e, roughness: 0.32, metalness: 0.55,
    envMapIntensity: 0.7, transparent: true, opacity: 0.72,
  })
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;

// Fake reflection: clone the hero, mirror across y=0, fade materials
const reflection = hero.clone(true);
reflection.traverse((o) => {
  if (o.isMesh) {
    o.castShadow = false;
    const m = o.material.clone();
    m.transparent = true; m.opacity = 0.16; m.depthWrite = false;
    if (m.envMapIntensity !== undefined) m.envMapIntensity *= 0.5;
    o.material = m;
  }
});
reflection.scale.y = -1;
reflection.position.y = -heroCenterY;   // mirror across the floor plane
// IMPORTANT: copy the hero's rotation.y; NEGATE its rotation.z

// Contact shadow: radial-alpha ShaderMaterial disc at y=0.012, depthWrite false
// Light styles: rgba(0.32,0.34,0.4, a*0.42) — Apple AO pools are never black
// Dark styles: rgba(0,0,0.02, a*0.55)
```

## 2. Recursive tree

Collect segments + leaf tips first, then build meshes. Recursion depth 4,
~110-160 segments. NEVER let a recursive function compute parent positions by
calling itself — precompute at module load (stack overflow risk).

```js
const grow = (pos, dir, length, radius, depth) => {
  const curved = dir.clone().add(new THREE.Vector3(
    (nextRand() - 0.5) * 0.25, 0.06 + nextRand() * 0.08, (nextRand() - 0.5) * 0.25
  )).normalize();
  const end = pos.clone().add(curved.clone().multiplyScalar(length));
  segments.push({ start: pos.clone(), end, r0: radius, r1: radius * 0.62 });
  if (depth >= 4) { leafTips.push({ p: end, s: 1 }); return; }
  if (depth === 3) leafTips.push({ p: end, s: 0.7 });   // mid-canopy density
  const n = depth === 0 ? 4 : 2 + (nextRand() > 0.45 ? 1 : 0);
  for (let c = 0; c < n; c++) {
    const axis = new THREE.Vector3(nextRand()-0.5, nextRand()-0.5, nextRand()-0.5).normalize();
    const childDir = curved.clone().applyAxisAngle(axis, 0.45 + nextRand() * 0.5);
    if (childDir.y < 0.05) childDir.y = 0.05 + nextRand() * 0.2;  // no droop
    grow(pos.clone().lerp(end, 0.85), childDir.normalize(),
         length * (0.6 + nextRand() * 0.12), radius * 0.58, depth + 1);
  }
};
// Segments → CylinderGeometry(r1, r0, len) at midpoint,
// quaternion.setFromUnitVectors(up, dir.normalize())
// Foliage: instanced vertex-perturbed IcosahedronGeometry(1,1) blobs at tips,
// per-instance color lerp dark→light green via setColorAt.
```

## 3. Instanced grass / flowers / foliage

InstancedMesh for anything repeated 50+ times. Per-instance color:
`mesh.setColorAt(i, color)` with material color 0xffffff, then
`if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;`

Flowers (stems + 5-petal heads + centers as three InstancedMeshes):
- Petal geometry: `SphereGeometry(1,10,8)` scaled `(0.085, 0.02, 0.15)`,
  translated `(0,0,0.13)` so it pivots at the flower center.
- Petal orientation: `Euler(-0.5, -angle, 0, 'YXZ')` — yaw first, then tilt.
- **HERO PRESENCE RULE:** if flowers (or any element) are NAMED in the prompt,
  they must pass the validator's presence check. 560 flowers at scale 1.0-1.9
  reads as "a flower meadow"; 240 small ones is invisible (~0.08% of pixels).

Grass: 4000-5000 cone blades, wind lean
`Math.sin(time*2 + x*0.3 + z*0.2) * 0.12`, per-instance green variance.

## 4. Horizon elements & the FOV rule ⚠️

The #1 composition failure: background hills/walls scaled intuitively end up
filling the ENTIRE sky as a green wall.

Before placing any background element, validate mathematically:

```js
import { visibleHeightAt } from './pipeline.mjs';
const distToHill = camera.position.distanceTo(hillPos);
const maxHillHeight = 0.35 * visibleHeightAt(camera, distToHill);
// A hill's visible height above ground must stay below maxHillHeight,
// or it walls off the sky. Sink hills: position.y = -height * 0.35.
```

Working values for a camera at y≈2.6, fov 42, hills at z −90…−110:
scale heights 6-9, widths 45-70, position.y = -h*0.35. NOT heights 14-22.

## 5. Rotation gotchas

- Compound Euler rotations on meshes/groups cause wrong orientations.
  BAKE rotations into geometry: `geometry.rotateX/Y/Z(...)` before creating
  the mesh. Example: torus arcs centered over the top:
  `TorusGeometry(r, tube, 24, 96, arc)` then `geo.rotateZ(-(arc - Math.PI)/2)`.
- Cylinder between two points: `CylinderGeometry(rTop, rBottom, len)` at the
  midpoint + `quaternion.setFromUnitVectors(new Vector3(0,1,0), dir)`.
- Attaching partial torus arcs tangentially to another torus by eyeballed
  rotateZ offsets produces floating misaligned geometry. Prefer end-cap
  spheres / straight stems at computed arc-end positions:
  `(R*cos(a), R*sin(a), 0)`.

## 6. Common hero objects

**Headphones:** headband = torus arc (rule above), chrome end-cap spheres at
arc ends, cylinder stems down to cups; cups = flattened spheres
(`scale(0.44,1,1)`), cushion tori rotated `rotateY(PI/2)`, thin trim ring +
center dot on outer faces. 3/4 hero angle: `rotation.y ≈ -0.5`, tiny
`rotation.z ≈ 0.03` to avoid CAD-perfect stiffness.

**Sneaker:** sole = extruded rounded box (BoxGeometry + heavy bevel illusion via
stacked scaled boxes), upper = LatheGeometry half + flattened spheres for toe,
laces = small instanced tori. Same stage as headphones.

**Crystals/gems:** OctahedronGeometry(r, 0) stretched on Y, MeshPhysicalMaterial
with transmission unsupported in WebGL1 — use transparent opacity 0.7,
roughness 0.1, strong env map instead.

**Buildings (city):** instanced boxes, emissive window texture faked with
per-instance emissive intensity variance on a second InstancedMesh of small
planes; validate skyline height against the FOV rule.
