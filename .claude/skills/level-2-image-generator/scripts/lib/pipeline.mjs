// pipeline.mjs — shared headless Three.js rendering pipeline
// Scenes import from this file and ONLY write scene content.
// Do not modify: every line here encodes a hard-won constraint.
//
// Requires: three@0.152.2, gl@8.1.6 (WebGL1), pngjs, sharp. Run under xvfb-run.
import createGL from 'gl';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { PNG } from 'pngjs';
import fs from 'fs';
import sharp from 'sharp';

// Aspect ratio presets (the only three supported)
export const ASPECTS = {
  '1:1': { width: 1080, height: 1080 },
  '16:9': { width: 1920, height: 1080 },
  '9:16': { width: 1080, height: 1920 },
};

// Deterministic randomness — never use Math.random()
export const seededRandom = (seed) => {
  const x = Math.sin(seed * 9999) * 10000;
  return x - Math.floor(x);
};

/**
 * Create a headless renderer.
 * @param {'1:1'|'16:9'|'9:16'} aspect
 * @param {object} opts
 * @param {number} opts.ss  Supersampling factor (default 2). headless-gl has no
 *                          MSAA, so we render at ss× and downscale (Lanczos3).
 * @param {number} opts.exposure  ACES tone mapping exposure. Style presets set this.
 * @returns {{ renderer, glContext, W, H, OUT_W, OUT_H }}
 */
export function createRenderer(aspect, { ss = 2, exposure = 1.15 } = {}) {
  const preset = ASPECTS[aspect];
  if (!preset) throw new Error(`Unknown aspect "${aspect}". Use 1:1, 16:9, or 9:16.`);
  const OUT_W = preset.width;
  const OUT_H = preset.height;
  const W = OUT_W * ss;
  const H = OUT_H * ss;

  const glContext = createGL(W, H, { preserveDrawingBuffer: true, antialias: false });
  if (!glContext) {
    throw new Error('Failed to create GL context. Are you running under xvfb-run?');
  }

  const fakeCanvas = {
    width: W, height: H, style: {},
    addEventListener() {}, removeEventListener() {},
    getContext() { return glContext; },
  };

  const renderer = new THREE.WebGLRenderer({
    canvas: fakeCanvas,
    context: glContext,
    antialias: false,
  });
  renderer.setSize(W, H, false);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  return { renderer, glContext, W, H, OUT_W, OUT_H };
}

/**
 * Add a studio environment map (PMREM + RoomEnvironment) for glossy/metallic
 * reflections. Call for product/studio scenes; optional for outdoor scenes
 * (use envMapIntensity <= 0.3 on outdoor materials either way).
 */
export function addStudioEnvironment(renderer, scene, blur = 0.04) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), blur).texture;
}

/**
 * Render one frame and write the final PNG.
 * Handles: GL bottom-left origin (vertical flip), forced opaque alpha,
 * SSAA downscale via sharp Lanczos3.
 */
export async function captureFrame({ renderer, glContext, scene, camera, W, H, OUT_W, OUT_H, outPath }) {
  renderer.render(scene, camera);

  const pixels = new Uint8Array(W * H * 4);
  glContext.readPixels(0, 0, W, H, glContext.RGBA, glContext.UNSIGNED_BYTE, pixels);

  const png = new PNG({ width: W, height: H });
  for (let y = 0; y < H; y++) {
    const src = (H - 1 - y) * W * 4; // vertical flip — GL origin is bottom-left
    png.data.set(pixels.subarray(src, src + W * 4), y * W * 4);
  }
  for (let i = 3; i < png.data.length; i += 4) png.data[i] = 255; // force opaque

  const rawPath = outPath.replace(/\.png$/, '.raw.png');
  fs.writeFileSync(rawPath, PNG.sync.write(png));

  await sharp(rawPath)
    .resize(OUT_W, OUT_H, { kernel: 'lanczos3' })
    .png()
    .toFile(outPath);

  fs.unlinkSync(rawPath);
  return outPath;
}

/**
 * FOV sanity helper for horizon/background elements.
 * Returns the world-space height visible at `distance` in front of the camera.
 * Rule: any background element (hills, buildings, walls) taller than
 * ~0.35 * visibleHeightAt(itsDistance) will wall off the sky. Validate before placing.
 */
export function visibleHeightAt(camera, distance) {
  const vFov = (camera.fov * Math.PI) / 180;
  return 2 * Math.tan(vFov / 2) * distance;
}

export { THREE };
