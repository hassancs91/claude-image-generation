"""
REFERENCE EXAMPLE - Soft, Apple-style carousel slide (1:1)
Prompt this stands in for: "soft minimalist carousel slide, Apple style, light
and airy, a soft gradient orb, refined type".

Shows: a light background with faint pastel glows, a gradient_sphere (soft orb
with volume + contact shadow), refined centered type, and carousel page dots.
Run: python3 soft_carousel.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from render import Design

d = Design("1:1")                          # 1500 x 1500

CHAR = (29, 29, 31); GRAY = (112, 112, 118); ACCENT = (111, 116, 230)
DOTG = (212, 212, 218)
ORB = [(255, 202, 181), (209, 187, 240), (179, 202, 245)]   # peach -> lavender -> periwinkle

# --- soft light background + faint pastel glows ---
d.linear_gradient([(0.0, (253, 253, 255)), (1.0, (241, 242, 248))], angle=90)
d.overlay_glow((0.5, 0.375), (236, 230, 250), radius=0.40, strength=0.16, mode="blend")
d.overlay_glow((0.30, 0.86), (252, 238, 232), radius=0.36, strength=0.10, mode="blend")

# --- the soft hero orb (diagonal pastel blend + gentle volume + contact shadow) ---
d.gradient_sphere(0.5, 0.375, 0.185, ORB, light=(-0.34, -0.34),
                  shadow=True, shadow_alpha=0.40, specular=0.16, rim=0.05)

# --- refined centered type ---
d.write(0.5, 0.118, "THE CRAFT \u00B7 02", role="grotesque", size=22, align="center",
        color=ACCENT, tracking=9)
hs = int(0.058 * d.W)
d.write(0.5, 0.665, "Designed to feel", role="grotesque", weight="bold", size=hs, align="center", color=CHAR)
d.write(0.5, 0.665 + hs * 1.06 / d.H, "effortless.", role="grotesque", weight="bold", size=hs,
        align="center", color=CHAR)
d.text_block(0.5, 0.815, "The best details are the ones you never notice.",
             role="grotesque", size=int(0.0215 * d.W), align="center", color=GRAY, max_frac=0.82)

# --- carousel page dots (active = pill) ---
dr, gap, dy = 0.0058, 0.030, 0.930
x0 = 0.5 - (4 * gap) / 2
for i in range(5):
    cx = x0 + i * gap
    if i == 1:
        d.rect(cx - dr * 2.2, dy - dr, cx + dr * 2.2, dy + dr, ACCENT, radius=dr)
    else:
        d.disk(cx, dy, dr, DOTG)

d.save(os.path.join(os.path.dirname(__file__), "out_soft.png"), grain=1.8, contrast=1.015)
print("wrote out_soft.png")
