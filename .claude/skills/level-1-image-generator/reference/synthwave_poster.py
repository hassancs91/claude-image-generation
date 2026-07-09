"""
REFERENCE EXAMPLE - Synthwave / outrun poster (1:2)
Prompt this stands in for: "synthwave poster, neon grid horizon, gradient sun,
chrome title, starfield, looks like album art".

Shows: linear gradient sky, additive glows, a custom striped sun (numpy layer),
a perspective neon grid, a starfield, and CHROME title type (gradient + glow +
stroke). Run:  python3 synthwave_poster.py
"""
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from render import Design, lerp_stops

d = Design("1:2")                      # 1080 x 2160
W, Hs, Ws = d.W, d.Hs, d.Ws
HY = 0.60                               # horizon (fraction of height)
SUN = (0.5, 0.50, 0.20)                # sun cx, cy, r (r as fraction of width)

# --- sky: deep indigo -> magenta band at the horizon ---
d.linear_gradient([
    (0.00, (7, 3, 24)), (0.30, (34, 14, 74)), (0.50, (96, 26, 110)),
    (0.585, (176, 55, 126)), (0.60, (222, 96, 148)),
    (0.62, (40, 14, 60)), (0.80, (16, 6, 34)), (1.00, (6, 2, 18)),
], angle=90)

xx, yy = d.coords()
below = np.where(yy <= d.Y(HY), 1.0, np.exp(-((yy - d.Y(HY)) / (0.05 * Hs)) ** 2))

# --- sun glow + horizon glow (additive) ---
d.overlay_glow((SUN[0], SUN[1]), (255, 90, 150), radius=SUN[2] * 1.3, strength=0.55, mode="add")
d.overlay_glow((0.5, HY), (255, 120, 170), radius=0.7, strength=0.30, mode="add")

# --- starfield (numpy points in the upper sky) ---
rng = np.random.default_rng(7)
stars = np.zeros((Hs, Ws), np.float32)
for _ in range(500):
    sxp = rng.integers(0, Ws); syp = rng.integers(0, int(d.Y(HY) - 0.06 * Hs))
    if math.hypot(sxp - d.X(SUN[0]), syp - d.Y(SUN[1])) < d.S(SUN[2]) * 1.25 and rng.random() < 0.7:
        continue
    stars[syp:syp + d.ss, sxp:sxp + d.ss] = rng.integers(90, 255)
base = d.get_rgb()
base = 255 - (255 - base) * (255 - stars[..., None] * np.array([1, 1, 1.05])) / 255
d.set_rgb(base)

# --- the sun: vertical gradient disc with venetian-blind stripes on its lower half ---
R = d.S(SUN[2]); ox, oy = d.X(SUN[0]), d.Y(SUN[1])
y0, y1 = int(oy - R), int(oy + R)
sun_rgb = np.zeros((Hs, Ws, 3), np.float32)
grad = lerp_stops(np.linspace(0, 1, y1 - y0), [
    (0.00, (255, 245, 202)), (0.15, (255, 216, 98)), (0.35, (255, 152, 62)),
    (0.58, (255, 94, 134)), (0.84, (255, 48, 112)), (1.00, (231, 27, 97))])
sun_rgb[y0:y1] = grad[:, None, :]
dist = np.sqrt((xx - ox) ** 2 + (yy - oy) ** 2)
solid = np.ones((Hs,), bool)
p, i = oy - 0.05 * R, 0
while p < y1 + 60:
    bh = max(3, 30 - i * 2.4) * d.ss; gh = (4 + i * 3.5) * d.ss
    g0, g1 = int(p + bh), int(p + bh + gh)
    solid[max(0, g0):max(0, g1)] = False
    p += bh + gh; i += 1
arows = solid.astype(np.float32); arows[:int(oy - 0.05 * R)] = 1.0
alpha = np.where((dist <= R) & (yy <= d.Y(HY)), arows[:, None], 0.0) * 255
d.composite_rgba(np.dstack([sun_rgb, alpha]))

# thin bright limb on the sun's upper edge
limb = np.exp(-((dist - R) ** 2) / (2 * (3.0 * d.ss) ** 2)) * np.clip((oy - yy) / R, 0, 1) ** 0.7
limb = np.where(yy <= d.Y(HY), limb, 0)
d.set_rgb(np.clip(d.get_rgb() + limb[..., None] * np.array([255, 238, 210]) * 0.9, 0, 255))

# --- neon perspective grid below the horizon ---
GRID = (255, 43, 143)
vx, vy = d.X(0.5), d.Y(HY)
bx = -W
while bx <= 2 * W:
    d.line(bx / W, 1.0, 0.5, HY, 0.0028, GRID, glow={"color": GRID, "size": 0.02 * Ws})
    bx += 94
N = 26
for k in range(1, N + 1):
    gy = HY + (1 - HY) * (k / N) ** 2.15
    d.line(0.0, gy, 1.0, gy, 0.002 + (k / N) * 0.003, GRID)

# --- chrome title (two lines) + kicker + tag ---
CHROME = [(0.00, (150, 196, 255)), (0.20, (206, 230, 255)), (0.42, (255, 255, 255)),
          (0.50, (255, 255, 255)), (0.57, (255, 226, 138)), (0.69, (255, 150, 70)),
          (0.85, (255, 70, 130)), (1.00, (203, 24, 92))]
size = d.fit_size("HORIZON", 0.86, role="display", weight="bold")
d.write(0.5, 0.20, "NEON", role="display", weight="bold", size=size, align="center",
        gradient=CHROME, stroke=8, stroke_color=(17, 6, 38), glow={"color": (255, 45, 150)})
d.write(0.5, 0.20 + size * 0.78 / d.H, "HORIZON", role="display", weight="bold", size=size,
        align="center", gradient=CHROME, stroke=8, stroke_color=(17, 6, 38),
        glow={"color": (255, 45, 150)})
d.write(0.5, 0.085, "//  R E T R O W A V E  //", role="mono", size=30, align="center",
        color=(150, 235, 255), tracking=4, glow={"color": (40, 180, 235)})
d.write(0.5, 0.965, "SIDE A \u00B7 1986", role="pixel", size=22, align="center",
        color=(150, 225, 255), tracking=6, glow={"color": (60, 150, 220)})

d.save(os.path.join(os.path.dirname(__file__), "out_synthwave.png"),
       grain=5, chroma=2, scanlines=0.035, saturation=1.08, contrast=1.03)
print("wrote out_synthwave.png")
