// validate.mjs — programmatic self-validation for rendered frames.
// Usage:
//   node validate.mjs <image.png> [heroSpec.json]
//
// heroSpec.json format (optional):
// [
//   { "name": "tree canopy", "hex": "5a9440", "tolerance": 60, "minPct": 2.0 },
//   { "name": "pink flowers", "hex": "f5a8c8", "tolerance": 45, "minPct": 0.15 }
// ]
// minPct = minimum % of sampled pixels that must match within tolerance
// (per-channel absolute distance). A named hero element that fails is
// effectively invisible in the frame and MUST be fixed before delivery.
import sharp from 'sharp';
import fs from 'fs';

const [, , imgPath, specPath] = process.argv;
if (!imgPath) {
  console.error('Usage: node validate.mjs <image.png> [heroSpec.json]');
  process.exit(1);
}

const { data, info } = await sharp(imgPath).raw().toBuffer({ resolveWithObject: true });
const { width, height, channels } = info;
const px = (x, y) => {
  const i = (y * width + x) * channels;
  return [data[i], data[i + 1], data[i + 2]];
};

// ---------------------------------------------------------------------------
// 1. Exposure / histogram check
// ---------------------------------------------------------------------------
const buckets = [0, 0, 0, 0, 0];
let total = 0;
let min = 255, max = 0;
for (let y = 0; y < height; y += 5) {
  for (let x = 0; x < width; x += 5) {
    const [r, g, b] = px(x, y);
    const lum = Math.round(0.2126 * r + 0.7152 * g + 0.0722 * b);
    buckets[Math.min(4, Math.floor(lum / 52))]++;
    if (lum < min) min = lum;
    if (lum > max) max = lum;
    total++;
  }
}
const pct = buckets.map((b) => ((b / total) * 100).toFixed(1));
console.log(`SIZE ${width}x${height}`);
console.log(`LUMINANCE min=${min} max=${max}`);
console.log(`HISTOGRAM  0-51: ${pct[0]}%  52-103: ${pct[1]}%  104-155: ${pct[2]}%  156-207: ${pct[3]}%  208-255: ${pct[4]}%`);

const warnings = [];
if (buckets[4] / total > 0.97) warnings.push('WASHED OUT: >97% of pixels are near-white. Lower exposure/ambient or darken materials.');
if (buckets[0] / total > 0.97) warnings.push('TOO DARK: >97% of pixels are near-black. Raise exposure or add lights.');
if (max - min < 60) warnings.push('LOW CONTRAST: luminance range < 60. Scene likely lacks a visible subject.');

// ---------------------------------------------------------------------------
// 2. ASCII luminance map (composition check without a visual preview)
// ---------------------------------------------------------------------------
console.log('\nASCII MAP (# dark, + mid-dark, . mid-light, space light):');
const cols = 80;
const rows = Math.round((cols * height) / width / 2.1); // ~terminal cell aspect
for (let ry = 0; ry < rows; ry++) {
  let row = '';
  for (let cx = 0; cx < cols; cx++) {
    const x = Math.min(width - 1, Math.round((cx / cols) * width));
    const y = Math.min(height - 1, Math.round((ry / rows) * height));
    const [r, g, b] = px(x, y);
    const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    row += lum < 60 ? '#' : lum < 130 ? '+' : lum < 200 ? '.' : ' ';
  }
  console.log(row);
}

// ---------------------------------------------------------------------------
// 3. Hero element presence check
// ---------------------------------------------------------------------------
let failed = false;
if (specPath && fs.existsSync(specPath)) {
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  console.log('\nHERO ELEMENT PRESENCE:');
  for (const hero of spec) {
    const tr = parseInt(hero.hex.slice(0, 2), 16);
    const tg = parseInt(hero.hex.slice(2, 4), 16);
    const tb = parseInt(hero.hex.slice(4, 6), 16);
    const tol = hero.tolerance ?? 50;
    let hits = 0;
    for (let y = 0; y < height; y += 3) {
      for (let x = 0; x < width; x += 3) {
        const [r, g, b] = px(x, y);
        if (Math.abs(r - tr) < tol && Math.abs(g - tg) < tol && Math.abs(b - tb) < tol) hits++;
      }
    }
    const sampled = Math.ceil(height / 3) * Math.ceil(width / 3);
    const hitPct = (hits / sampled) * 100;
    const ok = hitPct >= hero.minPct;
    if (!ok) failed = true;
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${hero.name}: ${hitPct.toFixed(2)}% (needs >= ${hero.minPct}%)`);
  }
}

if (warnings.length) {
  console.log('\nWARNINGS:');
  warnings.forEach((w) => console.log('  ' + w));
}

console.log(`\nRESULT: ${failed || warnings.length ? 'NEEDS FIXES' : 'OK'}`);
process.exit(failed ? 2 : 0);
